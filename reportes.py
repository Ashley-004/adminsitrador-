from flask import Blueprint, render_template, send_file,request
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import mysql.connector

# =====================
# CONEXIÓN DIRECTA (para evitar circular import)
# =====================
def obtener_conexion():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="parrilla51"
    )

# =====================
# BLUEPRINT
# =====================
reportes_bp = Blueprint("reportes", __name__)

@reportes_bp.route("/")
def reportes():
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id_pedido, u.nombre, u.apellido, p.fecha, p.total, p.estado
        FROM pedidos p
        INNER JOIN usuarios u ON p.cod_usuario = u.id_usuario
    """)
    pedidos = cursor.fetchall()
    conexion.close()
    return render_template("reportes.html", pedidos=pedidos)

# =====================
# EXPORTAR EXCEL
# =====================
@reportes_bp.route("/exportar_excel")
def exportar_excel():
    conexion = obtener_conexion()
    query = """
        SELECT p.id_pedido, u.nombre, u.apellido, p.fecha, p.total, p.estado
        FROM pedidos p
        INNER JOIN usuarios u ON p.cod_usuario = u.id_usuario
    """
    df = pd.read_sql(query, conexion)
    conexion.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="ReportePedidos")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="reporte_pedidos.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =====================
# EXPORTAR PDF
# =====================
@reportes_bp.route('/exportar_pdf')
def exportar_pdf():
    conexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="parrilla51"
    )
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id_pedido, u.nombre, u.apellido, p.fecha, p.total, p.estado
        FROM pedidos p
        INNER JOIN usuarios u ON p.cod_usuario = u.id_usuario
    """)
    pedidos = cursor.fetchall()
    cursor.close()
    conexion.close()

    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de Pedidos - Parrilla 51", ln=True, align="C")
    pdf.ln(10)

    for pedido in pedidos:
        texto = (
            f"Pedido #{pedido['id_pedido']} | "
            f"{pedido['nombre']} {pedido['apellido']} | "
            f"Fecha: {pedido['fecha']} | "
            f"Total: ${pedido['total']} | "
            f"Estado: {pedido['estado']}"
        )
        pdf.multi_cell(0, 10, texto)
        pdf.ln(5)

    # ✅ CORRECCIÓN: generar PDF en memoria
    salida = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    salida.write(pdf_bytes)
    salida.seek(0)

    return send_file(
        salida,
        as_attachment=True,
        download_name="reporte_pedidos.pdf",
        mimetype="application/pdf"
    )

@reportes_bp.route("/", methods=["GET", "POST"])
def ver_reportes():  # renombré para evitar conflicto de endpoint
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    # Valores por defecto
    busqueda = ""
    filtro_mes = ""
    filtro_estado = ""

    # Si vienen datos por POST
    if request.method == "POST":
        busqueda = request.form.get("busqueda", "").strip()
        filtro_mes = request.form.get("mes", "")
        filtro_estado = request.form.get("estado", "")

    # Construir la consulta base
    query = """
        SELECT p.id_pedido, u.nombre, u.apellido, p.fecha, p.total, p.estado
        FROM pedidos p
        INNER JOIN usuarios u ON p.cod_usuario = u.id_usuario
        WHERE 1=1
    """
    params = []

    # Aplicar filtros si existen
    if busqueda:
        query += " AND (u.nombre LIKE %s OR u.apellido LIKE %s OR p.estado LIKE %s)"
        busqueda_param = f"%{busqueda}%"
        params.extend([busqueda_param, busqueda_param, busqueda_param])

    if filtro_mes:
        query += " AND DATE_FORMAT(p.fecha, '%Y-%m') = %s"
        params.append(filtro_mes)

    if filtro_estado:
        query += " AND p.estado = %s"
        params.append(filtro_estado)

    query += " ORDER BY p.fecha DESC"

    cursor.execute(query, params)
    pedidos = cursor.fetchall()
    conexion.close()

    return render_template(
        "reportes.html",
        pedidos=pedidos,
        busqueda=busqueda,
        filtro_mes=filtro_mes,
        filtro_estado=filtro_estado
    )
