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

# Crear tablas al iniciar
Base.metadata.create_all(bind=engine)


# Helpers para historial
def now_iso():
    return datetime.utcnow().isoformat()


def write_historial(row_dict):
    """Append a row to historial.csv creating header if needed."""
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
        # no queremos que falle la app si no podemos escribir el historial
        print(f"Error escribiendo historial: {e}")


# Rutas
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        db = SessionLocal()
        usuario = db.query(Usuario).filter(Usuario.correo == correo).first()
        db.close()
        if usuario and check_password_hash(usuario.contrasena, contrasena):
            # Guardar información mínima en la sesión de Flask
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
    if request.method == "POST":
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = generate_password_hash(request.form['contrasena'])
        esAdmin = request.form.get('esAdmin') == 'on'
        session = SessionLocal()
        nuevo_usuario = Usuario(nombre=nombre, correo=correo, contrasena=contrasena, esAdmin=esAdmin)
        session.add(nuevo_usuario)
        try:
            session.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for("login"))
        except Exception as e:
            session.rollback()
            flash(f"Error: {str(e)}", "danger")
        finally:
            session.close()
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    nombre = session.get('usuario_nombre', 'Usuario')
    return render_template("dashboard.html", usuario=nombre)


@app.route("/productos/consultar", methods=["GET", "POST"])
def consultar_producto():
    session = SessionLocal()
    productos_data = []
    results_count = 0
    if request.method == "POST":
        codigo = request.form.get("codigo")
        if codigo:
            productos = session.query(Producto).filter(Producto.codigo == codigo).all()
        else:
            productos = session.query(Producto).all()

        # Construir una lista ligera para renderizado y evitar DetachedInstanceError
        for p in productos:
            productos_data.append(SimpleNamespace(id=p.id, nombre=p.nombre, codigo=p.codigo,
                                                   cantidad=p.cantidad, ubicacion=p.ubicacion))
        results_count = len(productos_data)

        # Guardar en historial la consulta
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

    session.close()
    return render_template("consultar_producto.html", productos=productos_data)


@app.route("/productos/<int:producto_id>", methods=["GET", "POST"])
def detalle_producto(producto_id):
    session = SessionLocal()
    producto = session.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        session.close()
        flash("Producto no encontrado", "danger")
        return redirect(url_for("consultar_producto"))

    # Registrar vista de detalle como consulta (GET)
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
                session.close()
                return render_template("detalle_producto.html", producto=producto_obj)

        ubicacion_raw = request.form.get("ubicacion")
        if ubicacion_raw is not None:
            producto.ubicacion = ubicacion_raw

        session.commit()
        # Guardar en historial la actualización
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
    session.close()
    return render_template("detalle_producto.html", producto=producto_obj)


@app.route('/historial')
def historial():
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
    return render_template('opciones.html')


@app.route('/logout')
def logout():
    # Limpiar sesión y redirigir
    session.clear()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))


@app.route('/admin')
def admin_panel():
    # Acceso prohibido si usuario no autenticado o no administrador
    if not session.get('user_id') or not session.get('esAdmin'):
        flash('Acceso denegado: se requiere privilegios de administrador', 'danger')
        return redirect(url_for('login'))
    return render_template('admin.html')


@app.route('/admin/productos')
def admin_productos():
    """Pantalla dedicada para gestionar (listar, editar, borrar) todos los productos."""
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
    # Crear nuevo producto (sólo admin)
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
    # comprobar existencia de código único
    existing = db.query(Producto).filter(Producto.codigo == codigo).first()
    if existing:
        db.close()
        flash('Código ya existe', 'danger')
        return redirect(url_for('admin_panel'))

    nuevo = Producto(nombre=nombre, codigo=codigo, cantidad=cantidad, ubicacion=ubicacion)
    db.add(nuevo)
    try:
        db.commit()
        # historial
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

    # GET -> mostrar formulario
    producto_obj = SimpleNamespace(id=producto.id, nombre=producto.nombre, codigo=producto.codigo,
                                   cantidad=producto.cantidad, ubicacion=producto.ubicacion)
    db.close()
    return render_template('admin_edit.html', producto=producto_obj)


@app.route('/admin/borrar/<int:producto_id>', methods=['POST'])
def admin_delete(producto_id):
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
