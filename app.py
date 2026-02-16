from flask import Flask, render_template, request, redirect, url_for, flash
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
        session = SessionLocal()
        usuario = session.query(Usuario).filter(Usuario.correo == correo).first()
        session.close()
        if usuario and check_password_hash(usuario.contrasena, contrasena):
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
        session = SessionLocal()
        nuevo_usuario = Usuario(nombre=nombre, correo=correo, contrasena=contrasena)
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
    return render_template("dashboard.html", usuario="Usuario")


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
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
