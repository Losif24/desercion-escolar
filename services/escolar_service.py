from sqlalchemy import case, func
from sqlalchemy.orm import contains_eager, selectinload

from constants import ESTADOS, ZONAS
from dao import estudiantes_dao, matriculas_dao
from models import CausaRetiro, Estudiante, Grupo, Institucion, Matricula, ProgramaApoyo


RETIRADOS = func.sum(case((Matricula.estado == "RETIRADO", 1), else_=0))


def _pct(valor):
    return f"{valor:.1f} %".replace(".", ",")


def matricula_actual(e):
    return max(e.matriculas, key=lambda m: (m.fecha, m.id_matricula), default=None)


def fila_estudiante(e):
    m = matricula_actual(e)
    g = m.grupo if m else None
    return {
        "id": e.id_estudiante,
        "nombre": f"{e.nombres} {e.apellidos}",
        "sexo": e.sexo,
        "zona": e.zona,
        "estrato": e.estrato,
        "discapacidad": bool(e.discapacidad),
        "id_institucion": g.id_institucion if g else None,
        "institucion": g.institucion.nombre if g else None,
        "grado": g.grado if g else None,
        "jornada": g.jornada if g else None,
        "estado": m.estado if m else None,
        "causa": m.causa.descripcion if m and m.causa else None,
        "programa": m.programa.nombre if m and m.programa else None,
    }


def estudiantes(zona=None, id_institucion=None):
    filas = [fila_estudiante(e) for e in estudiantes_dao.list_for_estudiantes(zona)]
    if id_institucion:
        filas = [f for f in filas if f["id_institucion"] == id_institucion]
    return filas


def estados_por_zona(filas):
    resumen = []
    for zona in ZONAS:
        de_zona = [f for f in filas if f["zona"] == zona]
        conteo = {estado: sum(f["estado"] == estado for f in de_zona) for estado in (*ESTADOS, None)}
        total = len(de_zona) or 1
        resumen.append({
            "zona": zona,
            "total": len(de_zona),
            "segmentos": [{"estado": estado, "n": n, "ancho": 100 * n / total}
                          for estado, n in conteo.items() if n],
        })
    return resumen


def matriculas_base(*columnas, zona=None, id_institucion=None):
    return matriculas_dao.base_query(*columnas, zona=zona, id_institucion=id_institucion)


def tasa_por(columna, **filtros):
    q = (matriculas_base(columna.label("nombre"), func.count(Matricula.id_matricula), RETIRADOS, **filtros)
         .group_by(columna))
    filas = []
    for nombre, matriculados, retirados in q:
        retirados = int(retirados or 0)
        filas.append({"nombre": "Sin dato" if nombre is None else str(nombre),
                      "matriculados": matriculados, "retirados": retirados,
                      "tasa": 100 * retirados / matriculados})
    return sorted(filas, key=lambda f: (-f["tasa"], f["nombre"]))


def retiros_por(columna, relacion, vacio, **filtros):
    q = (matriculas_base(columna, func.count(Matricula.id_matricula), **filtros)
         .outerjoin(relacion).filter(Matricula.estado == "RETIRADO").group_by(columna))
    filas = [{"nombre": nombre or vacio, "retirados": n} for nombre, n in q]
    return sorted(filas, key=lambda f: (-f["retirados"], f["nombre"]))


def lista_retirados(**filtros):
    q = (matriculas_base(Matricula, **filtros)
         .filter(Matricula.estado == "RETIRADO")
         .options(contains_eager(Matricula.estudiante),
                  contains_eager(Matricula.grupo).contains_eager(Grupo.institucion),
                  selectinload(Matricula.causa), selectinload(Matricula.programa))
         .order_by(Matricula.fecha.desc(), Estudiante.apellidos))
    return [{
        "id": m.id_estudiante,
        "nombre": f"{m.estudiante.nombres} {m.estudiante.apellidos}",
        "zona": m.estudiante.zona,
        "estrato": m.estudiante.estrato,
        "institucion": m.grupo.institucion.nombre,
        "grado": m.grupo.grado,
        "fecha": m.fecha.isoformat(),
        "causa": m.causa.descripcion if m.causa else None,
        "programa": m.programa.nombre if m.programa else None,
    } for m in q]


def desercion(zona=None, id_institucion=None):
    filtros = {"zona": zona, "id_institucion": id_institucion}
    total, retirados = matriculas_base(func.count(Matricula.id_matricula), RETIRADOS, **filtros).one()
    retirados = int(retirados or 0)
    activas = matriculas_base(func.count(Matricula.id_matricula), **filtros).filter(
        Matricula.estado == "ACTIVA").scalar()
    return {
        "totales": {"matriculas": total, "retirados": retirados, "activas": activas,
                    "tasa": 100 * retirados / total if total else 0},
        "por_institucion": tasa_por(Institucion.nombre, **filtros),
        "por_zona": tasa_por(Estudiante.zona, **filtros),
        "por_estrato": sorted(({**f, "nombre": f"Estrato {f['nombre']}"}
                               for f in tasa_por(Estudiante.estrato, **filtros)),
                              key=lambda f: f["nombre"]),
        "por_causa": retiros_por(CausaRetiro.descripcion, Matricula.causa, "Sin causa", **filtros),
        "por_programa": retiros_por(ProgramaApoyo.nombre, Matricula.programa, "Sin programa", **filtros),
        "retirados": lista_retirados(**filtros),
    }


def hallazgos(d):
    t = d["totales"]
    if not t["retirados"]:
        return ["No hay retiros registrados con estos filtros."]
    texto = [f"{t['retirados']} de {t['matriculas']} matrículas terminaron en retiro ({_pct(t['tasa'])})."]
    if d["por_causa"]:
        c = d["por_causa"][0]
        texto.append(f"La causa más frecuente es «{c['nombre']}»: {c['retirados']} de {t['retirados']} retiros.")
    if len(d["por_institucion"]) > 1:
        i = d["por_institucion"][0]
        texto.append(f"{i['nombre']} tiene la tasa más alta: {_pct(i['tasa'])} "
                     f"({i['retirados']} de {i['matriculados']}).")
    zonas = {z["nombre"]: z for z in d["por_zona"]}
    if "Rural" in zonas and "Urbana" in zonas:
        texto.append(f"Zona rural: {_pct(zonas['Rural']['tasa'])} frente a {_pct(zonas['Urbana']['tasa'])} en la urbana.")
    if d["por_estrato"]:
        e = max(d["por_estrato"], key=lambda f: f["tasa"])
        texto.append(f"{e['nombre']} concentra la tasa más alta: {_pct(e['tasa'])}.")
    sin_apoyo = next((p for p in d["por_programa"] if p["nombre"] == "Sin programa"), None)
    if sin_apoyo:
        n = sin_apoyo["retirados"]
        texto.append(f"{n} {'retirado no recibía' if n == 1 else 'retirados no recibían'} ningún programa de apoyo.")
    return texto


def barras_tasa(filas):
    tope = max((f["tasa"] for f in filas), default=0) or 1
    return [{"nombre": f["nombre"], "ancho": 100 * f["tasa"] / tope, "valor": _pct(f["tasa"]),
             "detalle": f"{f['retirados']} de {f['matriculados']} matrículas"} for f in filas]


def barras_conteo(filas):
    tope = max((f["retirados"] for f in filas), default=0) or 1
    return [{"nombre": f["nombre"], "ancho": 100 * f["retirados"] / tope, "valor": str(f["retirados"]),
             "detalle": f"{f['retirados']} {'retiro' if f['retirados'] == 1 else 'retiros'}"} for f in filas]
