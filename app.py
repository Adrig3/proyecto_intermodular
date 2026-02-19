"""
Aplicación Flask para gestión de inventario de almacén.

Permite a usuarios autenticados consultar, actualizar y gestionar productos.
Los administradores pueden crear, editar y eliminar productos.
Todas las acciones relevantes se registran en historial.csv para auditoría.

Librerías principales:
- Flask: framework web (rutas, renderizado, sesiones, mensajes flash)
- SQLAlchemy: ORM para acceso a base de datos
- Werkzeug: hashing seguro de contraseñas (generate_password_hash, check_password_hash)
- types.SimpleNamespace: objetos ligeros para pasar datos a templates sin objetos ORM
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import Base, engine, SessionLocal
from models import Usuario, Producto
from werkzeug.security import generate_password_hash, check_password_hash
from types import SimpleNamespace
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

Base.metadata.create_all(bind=engine)


def now_iso():
    """
    Devuelve la fecha/hora actual en formato ISO 8601 (UTC).
    Usado como timestamp para cada entrada del historial de auditoría.
    """
    return datetime.utcnow().isoformat()


def write_historial(row_dict):
    """
    Añade una fila al archivo historial.csv, creando la cabecera si el archivo no existe.

    row_dict: diccionario con claves timestamp, action, producto_id, codigo, nombre,
              old_cantidad, new_cantidad, old_ubicacion, new_ubicacion, results_count.
    Si falla la escritura, se imprime el error pero la app continúa (no bloquea la operación).
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'historial.csv')
    fieldnames = [
        'timestamp', 'action', 'producto_id', 'codigo', 'nombre',
        'old_cantidad', 'new_cantidad', 'old_ubicacion', 'new_ubicacion', 'results_count'
    ]
    file_exists = os.path.exists(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            row = {k: row_dict.get(k, '') for k in fieldnames}
            writer.writerow(row)
    except Exception as e:
        print(f"Error escribiendo historial: {e}")


@app.route("/")
def home():
    """Redirige la ruta raíz a la página de login."""
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Gestiona inicio de sesión: GET muestra el formulario, POST valida credenciales.
    Usa check_password_hash (Werkzeug) para comparar contraseña en texto plano con el hash guardado.
    Al autenticarse correctamente, guarda user_id, nombre y esAdmin en session de Flask.
    """
    if request.method == "POST":
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        db = SessionLocal()
        usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
        db.close()
        if usuario and check_password_hash(usuario.contrasena, contrasena):
            session['user_id'] = usuario.id
            session['usuario_nombre'] = usuario.nombre
            session['esAdmin'] = bool(usuario.esAdmin)

            flash(f"Bienvenido, {usuario.nombre}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Correo o contraseña incorrectos", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Registro de nuevos usuarios. POST crea el usuario con contraseña hasheada
    (generate_password_hash) y redirige a login. El checkbox esAdmin define si es administrador.
    """
    if request.method == "POST":
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = generate_password_hash(request.form['contrasena'])
        esAdmin = request.form.get('esAdmin') == 'on'
        db_session = SessionLocal()
        nuevo_usuario = Usuario(nombre=nombre, correo=correo, contrasena=contrasena, esAdmin=esAdmin)
        db_session.add(nuevo_usuario)
        try:
            db_session.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db_session.rollback()
            flash(f"Error: {str(e)}", "danger")
        finally:
            db_session.close()
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    """Muestra el menú principal con opciones: consultar, historial, opciones y (si admin) panel admin."""
    nombre = session.get('usuario_nombre', 'Usuario')
    return render_template("dashboard.html", usuario=nombre)


@app.route("/productos/consultar", methods=["GET", "POST"])
def consultar_producto():
    """
    Búsqueda de productos: por código (POST) o lista todos si el campo está vacío.
    Usa SimpleNamespace para pasar datos a la plantilla sin objetos SQLAlchemy,
    evitando DetachedInstanceError al cerrar la sesión antes del render.
    Registra cada consulta en el historial.
    """
    db = SessionLocal()
    productos_data = []
    results_count = 0
    if request.method == "POST":
        codigo = request.form.get("codigo")
        if codigo:
            productos = db.query(Producto).filter(Producto.codigo == codigo).all()
        else:
            productos = db.query(Producto).all()

        for p in productos:
            productos_data.append(SimpleNamespace(id=p.id, nombre=p.nombre, codigo=p.codigo,
                                                   cantidad=p.cantidad, ubicacion=p.ubicacion))
        results_count = len(productos_data)

        write_historial({
            'timestamp': now_iso(),
            'action': 'consultar',
            'producto_id': '',
            'codigo': codigo if codigo else 'ALL',
            'nombre': '',
            'old_cantidad': '',
            'new_cantidad': '',
            'old_ubicacion': '',
            'new_ubicacion': '',
            'results_count': results_count,
        })

    db.close()
    return render_template("consultar_producto.html", productos=productos_data)


@app.route("/productos/<int:producto_id>", methods=["GET", "POST"])
def detalle_producto(producto_id):
    """
    Muestra detalle de un producto y permite actualizar cantidad y ubicación (POST).
    GET registra la vista en historial. POST valida cantidad numérica y persiste cambios.
    """
    db = SessionLocal()
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        db.close()
        flash("Producto no encontrado", "danger")
        return redirect(url_for("consultar_producto"))

    if request.method == "GET":
        write_historial({
            'timestamp': now_iso(),
            'action': 'ver_detalle',
            'producto_id': producto.id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'old_cantidad': '',
            'new_cantidad': '',
            'old_ubicacion': '',
            'new_ubicacion': '',
            'results_count': '',
        })

    if request.method == "POST":
        cantidad_raw = request.form.get("cantidad")
        old_cantidad = producto.cantidad
        old_ubicacion = producto.ubicacion

        if cantidad_raw is not None and cantidad_raw != "":
            try:
                producto.cantidad = int(cantidad_raw)
            except ValueError:
                flash("Cantidad inválida", "danger")
                producto_obj = SimpleNamespace(id=producto.id, nombre=producto.nombre,
                                               ubicacion=producto.ubicacion, cantidad=producto.cantidad)
                db.close()
                return render_template("detalle_producto.html", producto=producto_obj)

        ubicacion_raw = request.form.get("ubicacion")
        if ubicacion_raw is not None:
            producto.ubicacion = ubicacion_raw

        db.commit()
        write_historial({
            'timestamp': now_iso(),
            'action': 'actualizar',
            'producto_id': producto.id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'old_cantidad': old_cantidad,
            'new_cantidad': producto.cantidad,
            'old_ubicacion': old_ubicacion,
            'new_ubicacion': producto.ubicacion,
            'results_count': '',
        })
        flash("Producto actualizado", "success")

    producto_obj = SimpleNamespace(id=producto.id, nombre=producto.nombre,
                                   ubicacion=producto.ubicacion, cantidad=producto.cantidad)
    db.close()
    return render_template("detalle_producto.html", producto=producto_obj)


@app.route('/historial')
def historial():
    """
    Muestra el contenido de historial.csv en una tabla.
    csv.DictReader permite leer filas como diccionarios usando la primera fila como claves.
    """
    csv_path = os.path.join(os.path.dirname(__file__), 'historial.csv')
    rows = []
    if os.path.exists(csv_path):
        try:
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for r in reader:
                    rows.append(r)
        except Exception as e:
            flash(f"Error leyendo historial: {e}", "danger")
    return render_template('historial.html', rows=rows)


@app.route('/opciones')
def opciones():
    """Página de opciones del usuario (información y enlaces de vuelta/cerrar sesión)."""
    return render_template('opciones.html')


@app.route('/logout')
def logout():
    """Limpia la sesión de Flask (session.clear) y redirige al login."""
    session.clear()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))


@app.route('/admin')
def admin_panel():
    """Panel de administración: solo accesible si el usuario está autenticado y esAdmin."""
    if not session.get('user_id') or not session.get('esAdmin'):
        flash('Acceso denegado: se requiere privilegios de administrador', 'danger')
        return redirect(url_for('login'))
    return render_template('admin.html')


@app.route('/admin/productos')
def admin_productos():
    """
    Lista todos los productos para gestión (editar, borrar).
    Solo administradores. Usa SimpleNamespace para evitar DetachedInstanceError.
    """
    if not session.get('user_id') or not session.get('esAdmin'):
        flash('Acceso denegado: se requiere privilegios de administrador', 'danger')
        return redirect(url_for('login'))
    db = SessionLocal()
    productos = db.query(Producto).all()
    productos_data = [SimpleNamespace(id=p.id, nombre=p.nombre, codigo=p.codigo,
                                       cantidad=p.cantidad, ubicacion=p.ubicacion) for p in productos]
    db.close()
    return render_template('admin_productos.html', productos=productos_data)


@app.route('/admin/add', methods=['POST'])
def admin_add():
    """
    Crea un nuevo producto. Valida que el código sea único.
    Registra la acción 'crear' en el historial.
    """
    if not session.get('user_id') or not session.get('esAdmin'):
        flash('Acceso denegado: se requiere privilegios de administrador', 'danger')
        return redirect(url_for('login'))

    nombre = request.form.get('nombre')
    codigo = request.form.get('codigo')
    cantidad_raw = request.form.get('cantidad')
    ubicacion = request.form.get('ubicacion')

    try:
        cantidad = int(cantidad_raw) if cantidad_raw not in (None, '') else 0
    except ValueError:
        flash('Cantidad inválida', 'danger')
        return redirect(url_for('admin_panel'))

    db = SessionLocal()
    existing = db.query(Producto).filter(Producto.codigo == codigo).first()
    if existing:
        db.close()
        flash('Código ya existe', 'danger')
        return redirect(url_for('admin_panel'))

    nuevo = Producto(nombre=nombre, codigo=codigo, cantidad=cantidad, ubicacion=ubicacion)
    db.add(nuevo)
    try:
        db.commit()
        write_historial({
            'timestamp': now_iso(),
            'action': 'crear',
            'producto_id': nuevo.id,
            'codigo': codigo,
            'nombre': nombre,
            'old_cantidad': '',
            'new_cantidad': cantidad,
            'old_ubicacion': '',
            'new_ubicacion': ubicacion,
            'results_count': '',
        })
        flash('Producto creado', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error creando producto: {e}', 'danger')
    finally:
        db.close()

    return redirect(url_for('admin_panel'))


@app.route('/admin/editar/<int:producto_id>', methods=['GET', 'POST'])
def admin_edit(producto_id):
    """
    Edita un producto existente. GET muestra formulario con datos actuales.
    POST actualiza todos los campos y registra en historial con action 'actualizar_admin'.
    """
    if not session.get('user_id') or not session.get('esAdmin'):
        flash('Acceso denegado: se requiere privilegios de administrador', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        db.close()
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('admin_productos'))

    if request.method == 'POST':
        old_cantidad = producto.cantidad
        old_ubicacion = producto.ubicacion
        producto.nombre = request.form.get('nombre')
        producto.codigo = request.form.get('codigo')
        cantidad_raw = request.form.get('cantidad')
        try:
            producto.cantidad = int(cantidad_raw) if cantidad_raw not in (None, '') else 0
        except ValueError:
            db.close()
            flash('Cantidad inválida', 'danger')
            return redirect(url_for('admin_edit', producto_id=producto_id))
        producto.ubicacion = request.form.get('ubicacion')

        try:
            db.commit()
            write_historial({
                'timestamp': now_iso(),
                'action': 'actualizar_admin',
                'producto_id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'old_cantidad': old_cantidad,
                'new_cantidad': producto.cantidad,
                'old_ubicacion': old_ubicacion,
                'new_ubicacion': producto.ubicacion,
                'results_count': '',
            })
            flash('Producto actualizado', 'success')
        except Exception as e:
            db.rollback()
            flash(f'Error actualizando producto: {e}', 'danger')
        finally:
            db.close()
        return redirect(url_for('admin_productos'))

    producto_obj = SimpleNamespace(id=producto.id, nombre=producto.nombre, codigo=producto.codigo,
                                   cantidad=producto.cantidad, ubicacion=producto.ubicacion)
    db.close()
    return render_template('admin_edit.html', producto=producto_obj)


@app.route('/admin/borrar/<int:producto_id>', methods=['POST'])
def admin_delete(producto_id):
    """
    Elimina un producto de la base de datos.
    Registra la acción 'borrar' en historial con los datos previos a la eliminación.
    """
    if not session.get('user_id') or not session.get('esAdmin'):
        flash('Acceso denegado: se requiere privilegios de administrador', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        db.close()
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('admin_panel'))

    try:
        db.delete(producto)
        db.commit()
        write_historial({
            'timestamp': now_iso(),
            'action': 'borrar',
            'producto_id': producto_id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'old_cantidad': producto.cantidad,
            'new_cantidad': '',
            'old_ubicacion': producto.ubicacion,
            'new_ubicacion': '',
            'results_count': '',
        })
        flash('Producto eliminado', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error borrando producto: {e}', 'danger')
    finally:
        db.close()

    return redirect(url_for('admin_productos'))


if __name__ == "__main__":
    app.run(debug=True)
