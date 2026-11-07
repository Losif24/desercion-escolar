from sqlalchemy.orm import contains_eager, selectinload

from models import CausaRetiro, Estudiante, Grupo, Institucion, Matricula, ProgramaApoyo, db


class SessionDAO:
    def add(self, obj):
        db.session.add(obj)

    def delete(self, obj):
        db.session.delete(obj)

    def commit(self):
        db.session.commit()

    def rollback(self):
        db.session.rollback()

    def query(self, *columnas):
        return db.session.query(*columnas)


class InstitucionDAO:
    def get_optional(self, id_institucion):
        return db.session.get(Institucion, id_institucion) if id_institucion else None

    def exists(self, id_institucion):
        return bool(id_institucion and db.session.get(Institucion, id_institucion))

    def list_ordered(self):
        return Institucion.query.order_by(Institucion.nombre).all()

    def get_or_404(self, id_institucion):
        return db.get_or_404(Institucion, id_institucion)


class EstudianteDAO:
    def get_or_404(self, id_estudiante):
        return db.get_or_404(Estudiante, id_estudiante)

    def list_for_estudiantes(self, zona=None):
        q = (Estudiante.query
             .options(selectinload(Estudiante.matriculas).options(
                 selectinload(Matricula.grupo).selectinload(Grupo.institucion),
                 selectinload(Matricula.causa),
                 selectinload(Matricula.programa)))
             .order_by(Estudiante.apellidos, Estudiante.nombres))
        if zona:
            q = q.filter(Estudiante.zona == zona)
        return q.all()

    def list_ordered(self):
        return Estudiante.query.order_by(Estudiante.apellidos, Estudiante.nombres).all()


class GrupoDAO:
    def exists(self, id_grupo):
        return bool(id_grupo and db.session.get(Grupo, id_grupo))

    def list_for_form(self):
        return (Grupo.query.join(Grupo.institucion)
                .options(selectinload(Grupo.institucion))
                .order_by(Institucion.nombre, Grupo.anio_lectivo.desc(), Grupo.grado).all())

    def list_for_api(self, id_institucion=None):
        q = Grupo.query.options(selectinload(Grupo.institucion)).order_by(Grupo.anio_lectivo.desc(), Grupo.grado)
        if id_institucion:
            q = q.filter(Grupo.id_institucion == id_institucion)
        return q.all()

    def list_for_api_docs(self):
        return (Grupo.query.join(Grupo.institucion).options(contains_eager(Grupo.institucion))
                .order_by(Institucion.nombre, Grupo.anio_lectivo.desc(), Grupo.grado).all())

    def get_or_404(self, id_grupo):
        return db.get_or_404(Grupo, id_grupo)


class CausaRetiroDAO:
    def exists(self, id_causa):
        return bool(id_causa and db.session.get(CausaRetiro, id_causa))

    def list_ordered(self):
        return CausaRetiro.query.order_by(CausaRetiro.descripcion).all()

    def get_or_404(self, id_causa):
        return db.get_or_404(CausaRetiro, id_causa)


class ProgramaApoyoDAO:
    def exists(self, id_programa):
        return bool(id_programa and db.session.get(ProgramaApoyo, id_programa))

    def list_ordered(self):
        return ProgramaApoyo.query.order_by(ProgramaApoyo.nombre).all()

    def get_or_404(self, id_programa):
        return db.get_or_404(ProgramaApoyo, id_programa)


class MatriculaDAO:
    def base_query(self, *columnas, zona=None, id_institucion=None):
        q = (db.session.query(*columnas).select_from(Matricula)
             .join(Matricula.estudiante).join(Matricula.grupo).join(Grupo.institucion))
        if zona:
            q = q.filter(Estudiante.zona == zona)
        if id_institucion:
            q = q.filter(Grupo.id_institucion == id_institucion)
        return q


class CatalogoDAO:
    def get_or_404(self, modelo, item_id):
        return db.get_or_404(modelo, item_id)
