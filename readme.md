# Sistema de Gestión de Inventario para Almacén

Aplicación web móvil-first para la gestión de inventario de un almacén. Permite consultar productos, actualizar cantidades y ubicaciones, registrar usuarios y, en modo administrador, crear, editar y eliminar productos. Todas las acciones quedan registradas en un historial de auditoría.

**Autor:** Adrià Gari Sagrera

---

## Descripción

La aplicación está pensada para usarse en dispositivos móviles dentro del entorno de un almacén. Los operarios pueden iniciar sesión, buscar productos por código, ver detalles y actualizar la cantidad o ubicación. Los administradores tienen acceso adicional para dar de alta nuevos productos y gestionarlos (editar o borrar).

### Funcionalidades principales

- **Autenticación:** registro e inicio de sesión con contraseñas cifradas
- **Roles:** usuario estándar y administrador
- **Consulta de productos:** búsqueda por código o listado completo
- **Detalle y actualización:** ver y modificar cantidad y ubicación de cada producto
- **Historial:** registro en CSV de consultas, actualizaciones, altas y bajas
- **Panel de administración:** crear productos y pantalla dedicada para gestionar (editar/borrar) todos los productos

---

## Tecnologías

| Categoría     | Tecnología                          |
|---------------|-------------------------------------|
| Backend       | Python, Flask                       |
| Base de datos | SQLAlchemy (ORM), PostgreSQL        |
| Autenticación | Werkzeug (hash de contraseñas)      |
| Plantillas    | Jinja2                              |
| Configuración | python-dotenv                       |
| Frontend      | HTML, CSS (diseño Material Design)  |
| Auditoría     | CSV (historial de acciones)         |

---

## Estructura del proyecto

```
proyecto_intermodular/
├── app.py              # Aplicación Flask y rutas
├── database.py         # Configuración de SQLAlchemy y sesión
├── models.py           # Modelos Usuario y Producto
├── requirements.txt    # Dependencias Python
├── .env                # Variables de entorno (DATABASE_URL)
├── historial.csv       # Registro de acciones (se genera al usar la app)
├── static/
│   └── style.css       # Estilos globales
└── templates/
    ├── base.html       # Layout base con navbar
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── consultar_producto.html
    ├── detalle_producto.html
    ├── historial.html
    ├── opciones.html
    ├── admin.html          # Crear producto
    ├── admin_productos.html # Listar/editar/borrar productos
    └── admin_edit.html     # Formulario de edición
```

---

## Instalación

1. **Clonar el repositorio**

2. **Crear entorno virtual e instalar dependencias:**
   ```
   python -m venv entorno
   entorno\Scripts\activate   (Windows)
   pip install flask sqlalchemy psycopg2-binary python-dotenv
   ```

3. **Configurar la base de datos:** crear un archivo `.env` en la raíz con:
   ```
   DATABASE_URL=postgresql://usuario:password@host:puerto/nombre_bd
   ```

4. **Ejecutar la aplicación:**
   ```
   python app.py
   ```

5. Abrir el navegador en `http://127.0.0.1:5000` (o el puerto indicado en la consola).

---

## Uso

1. **Registro:** crear una cuenta en `/register`. Marcar "Es administrador" si se necesita acceso al panel admin.
2. **Login:** iniciar sesión en `/login`.
3. **Dashboard:** desde el menú se accede a Consultar, Historial y Opciones.
4. **Consultar productos:** buscar por código o ver todos; desde cada resultado se puede ver el detalle y actualizar cantidad/ubicación.
5. **Panel Admin:** solo visible para administradores. Permite crear productos y gestionar la lista completa en una pantalla dedicada.

---

## Notas

- El historial se guarda en `historial.csv` en la raíz del proyecto. Incluye timestamp, acción, producto afectado y valores anteriores/nuevos.
- Las contraseñas se almacenan hasheadas con Werkzeug.
- La interfaz sigue pautas de Material Design y está optimizada para uso en móvil.
