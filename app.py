import streamlit as st
import sqlite3
import datetime
import pandas as pd
import plotly.express as px
import os

# ── Base de datos ──
def init_db():
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            categoria TEXT,
            descripcion TEXT,
            monto REAL,
            metodo_pago TEXT,
            nota TEXT,
            fecha TEXT
        )
    ''')
    conn.commit()
    conn.close()

def agregar_movimiento(tipo, categoria, descripcion, monto, metodo_pago, nota):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO movimientos (tipo, categoria, descripcion, monto, metodo_pago, nota, fecha) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tipo, categoria, descripcion, monto, metodo_pago, nota, fecha))
    conn.commit()
    conn.close()

def obtener_movimientos(filtro_tipo=None, filtro_categoria=None, filtro_fecha=None, busqueda=None):
    conn = sqlite3.connect("data/gastos.db")
    query = "SELECT * FROM movimientos WHERE 1=1"
    params = []
    if filtro_tipo and filtro_tipo != "Todos":
        query += " AND tipo=?"
        params.append(filtro_tipo)
    if filtro_categoria and filtro_categoria != "Todas":
        query += " AND categoria=?"
        params.append(filtro_categoria)
    if filtro_fecha:
        query += " AND DATE(fecha)=?"
        params.append(filtro_fecha.strftime("%Y-%m-%d"))
    if busqueda:
        query += " AND (descripcion LIKE ? OR nota LIKE ?)"
        params.extend([f"%{busqueda}%", f"%{busqueda}%"])
    query += " ORDER BY fecha DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_resumen():
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    hoy = datetime.date.today().strftime("%Y-%m-%d")
    mes = datetime.date.today().strftime("%Y-%m")
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso'")
    ingresos_total = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Gasto'")
    gastos_total = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Gasto' AND DATE(fecha)=?", (hoy,))
    gastos_hoy = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Gasto' AND strftime('%Y-%m', fecha)=?", (mes,))
    gastos_mes = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso' AND strftime('%Y-%m', fecha)=?", (mes,))
    ingresos_mes = cursor.fetchone()[0] or 0
    conn.close()
    return ingresos_total, gastos_total, gastos_hoy, gastos_mes, ingresos_mes

def obtener_por_categoria():
    conn = sqlite3.connect("data/gastos.db")
    df = pd.read_sql_query("""
        SELECT categoria, SUM(monto) as total 
        FROM movimientos WHERE tipo='Gasto' 
        GROUP BY categoria
    """, conn)
    conn.close()
    return df

def obtener_por_mes():
    conn = sqlite3.connect("data/gastos.db")
    df = pd.read_sql_query("""
        SELECT strftime('%Y-%m', fecha) as mes, tipo, SUM(monto) as total
        FROM movimientos
        GROUP BY mes, tipo
        ORDER BY mes
    """, conn)
    conn.close()
    return df

def eliminar_movimiento(id):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movimientos WHERE id=?", (id,))
    conn.commit()
    conn.close()

# ── Inicializar ──
os.makedirs("data", exist_ok=True)
init_db()

CATEGORIAS = ["Comida", "Transporte", "Vivienda", "Salud", "Educación", "Entretenimiento", "Ropa", "Otros"]
METODOS_PAGO = ["Efectivo", "Tarjeta débito", "Tarjeta crédito", "Nequi", "Daviplata", "Transferencia", "Otro"]

# ── UI ──
st.title("💰 Gestor de Gastos")

tab1, tab2, tab3 = st.tabs(["Agregar", "Resumen", "Historial"])

with tab1:
    st.subheader("Agregar movimiento")
    tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso"])
    categoria = st.selectbox("Categoría:", CATEGORIAS) if tipo == "Gasto" else "Ingreso"
    descripcion = st.text_input("Descripción:")
    monto = st.number_input("Monto:", min_value=0.0, step=1000.0)
    metodo_pago = st.selectbox("Método de pago:", METODOS_PAGO)
    nota = st.text_area("Nota (opcional):", height=80)

    if st.button("Agregar"):
        if descripcion and monto > 0:
            agregar_movimiento(tipo, categoria, descripcion, monto, metodo_pago, nota)
            st.success(f"{tipo} de ${monto:,.0f} agregado correctamente")
        else:
            st.warning("Completa los campos obligatorios")

with tab2:
    st.subheader("Resumen")
    ingresos_total, gastos_total, gastos_hoy, gastos_mes, ingresos_mes = obtener_resumen()
    balance = ingresos_total - gastos_total

    col1, col2, col3 = st.columns(3)
    col1.metric("💵 Ingresos totales", f"${ingresos_total:,.0f}")
    col2.metric("💸 Gastos totales", f"${gastos_total:,.0f}")
    col3.metric("📊 Balance", f"${balance:,.0f}")

    col4, col5 = st.columns(2)
    col4.metric("📅 Gastos hoy", f"${gastos_hoy:,.0f}")
    col5.metric("🗓️ Gastos este mes", f"${gastos_mes:,.0f}")

    st.divider()

    # Gráfica torta
    st.subheader("Gastos por categoría")
    df_cat = obtener_por_categoria()
    if not df_cat.empty:
        fig1 = px.pie(df_cat, values="total", names="categoria",
                      color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No hay gastos registrados")

    # Gráfica ingresos vs gastos por mes
    st.subheader("Ingresos vs Gastos por mes")
    df_mes = obtener_por_mes()
    if not df_mes.empty:
        fig2 = px.bar(df_mes, x="mes", y="total", color="tipo", barmode="group",
                      color_discrete_map={"Ingreso": "#2ecc71", "Gasto": "#e74c3c"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No hay datos suficientes")

    # Gráfica evolución gastos por mes (línea)
    st.subheader("Evolución de gastos")
    if not df_mes.empty:
        df_gastos_mes = df_mes[df_mes["tipo"] == "Gasto"]
        if not df_gastos_mes.empty:
            fig3 = px.line(df_gastos_mes, x="mes", y="total", markers=True,
                           color_discrete_sequence=["#e74c3c"])
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No hay datos suficientes")

with tab3:
    st.subheader("Historial")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_tipo = st.selectbox("Tipo:", ["Todos", "Gasto", "Ingreso"])
    with col2:
        filtro_cat = st.selectbox("Categoría:", ["Todas"] + CATEGORIAS)
    with col3:
        usar_fecha = st.checkbox("Filtrar por fecha")
        filtro_fecha = st.date_input("Fecha:") if usar_fecha else None
    with col4:
        busqueda = st.text_input("🔍 Buscar:")

    df = obtener_movimientos(filtro_tipo, filtro_cat, filtro_fecha, busqueda)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        id_eliminar = st.number_input("ID a eliminar:", min_value=1, step=1)
        if st.button("Eliminar"):
            eliminar_movimiento(int(id_eliminar))
            st.success(f"Movimiento #{id_eliminar} eliminado")
            st.rerun()
    else:
        st.info("No hay movimientos con esos filtros")