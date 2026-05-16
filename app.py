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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presupuestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT UNIQUE,
            limite REAL
        )
    ''')
    # Insertar categorías por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        defaults = ["Comida", "Transporte", "Vivienda", "Salud", "Educación", "Entretenimiento", "Ropa", "Otros"]
        for cat in defaults:
            cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (cat,))
    conn.commit()
    conn.close()

def obtener_categorias():
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM categorias ORDER BY nombre")
    cats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cats

def agregar_categoria(nombre):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (nombre,))
    conn.commit()
    conn.close()

def eliminar_categoria(nombre):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categorias WHERE nombre=?", (nombre,))
    cursor.execute("DELETE FROM presupuestos WHERE categoria=?", (nombre,))
    conn.commit()
    conn.close()

def guardar_presupuesto(categoria, limite):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO presupuestos (categoria, limite) VALUES (?, ?)", (categoria, limite))
    conn.commit()
    conn.close()

def obtener_presupuestos():
    conn = sqlite3.connect("data/gastos.db")
    df = pd.read_sql_query("SELECT * FROM presupuestos", conn)
    conn.close()
    return df

def obtener_gasto_mes_categoria(categoria):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    mes = datetime.date.today().strftime("%Y-%m")
    cursor.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE tipo='Gasto' AND categoria=? AND strftime('%Y-%m', fecha)=?
    """, (categoria, mes))
    resultado = cursor.fetchone()[0] or 0
    conn.close()
    return resultado

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
        FROM movimientos GROUP BY mes, tipo ORDER BY mes
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

METODOS_PAGO = ["Efectivo", "Tarjeta débito", "Tarjeta crédito", "Nequi", "Daviplata", "Transferencia", "Otro"]

# ── UI ──
st.title("💰 Gestor de Gastos")

tab1, tab2, tab3, tab4 = st.tabs(["Agregar", "Resumen", "Historial", "⚙️ Configuración"])

CATEGORIAS = obtener_categorias()

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

    # Presupuestos
    df_presupuestos = obtener_presupuestos()
    if not df_presupuestos.empty:
        st.subheader("🎯 Presupuestos del mes")
        for _, row in df_presupuestos.iterrows():
            gastado = obtener_gasto_mes_categoria(row["categoria"])
            limite = row["limite"]
            porcentaje = min(gastado / limite, 1.0) if limite > 0 else 0
            col1, col2 = st.columns([3, 1])
            with col1:
                if porcentaje >= 1.0:
                    st.error(f"🚨 {row['categoria']} — Límite superado!")
                elif porcentaje >= 0.8:
                    st.warning(f"⚠️ {row['categoria']} — Cerca del límite")
                else:
                    st.write(f"✅ {row['categoria']}")
                st.progress(porcentaje)
            with col2:
                st.write(f"${gastado:,.0f} / ${limite:,.0f}")

        st.divider()

    # Gráficas
    st.subheader("Gastos por categoría")
    df_cat = obtener_por_categoria()
    if not df_cat.empty:
        fig1 = px.pie(df_cat, values="total", names="categoria",
                      color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No hay gastos registrados")

    st.subheader("Ingresos vs Gastos por mes")
    df_mes = obtener_por_mes()
    if not df_mes.empty:
        fig2 = px.bar(df_mes, x="mes", y="total", color="tipo", barmode="group",
                      color_discrete_map={"Ingreso": "#2ecc71", "Gasto": "#e74c3c"})
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Evolución de gastos")
    if not df_mes.empty:
        df_gastos_mes = df_mes[df_mes["tipo"] == "Gasto"]
        if not df_gastos_mes.empty:
            fig3 = px.line(df_gastos_mes, x="mes", y="total", markers=True,
                           color_discrete_sequence=["#e74c3c"])
            st.plotly_chart(fig3, use_container_width=True)

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

with tab4:
    st.subheader("⚙️ Configuración")

    # Categorías
    st.markdown("### 🗂️ Categorías")
    col1, col2 = st.columns(2)
    with col1:
        nueva_cat = st.text_input("Nueva categoría:")
        if st.button("Agregar categoría"):
            if nueva_cat:
                agregar_categoria(nueva_cat)
                st.success(f"Categoría '{nueva_cat}' agregada")
                st.rerun()
            else:
                st.warning("Escribe un nombre")
    with col2:
        cat_eliminar = st.selectbox("Eliminar categoría:", CATEGORIAS)
        if st.button("Eliminar categoría"):
            eliminar_categoria(cat_eliminar)
            st.success(f"Categoría '{cat_eliminar}' eliminada")
            st.rerun()

    st.divider()

    # Presupuestos
    st.markdown("### 🎯 Presupuestos mensuales")
    cat_presupuesto = st.selectbox("Categoría:", CATEGORIAS, key="pres_cat")
    limite = st.number_input("Límite mensual:", min_value=0.0, step=10000.0, key="pres_limite")
    if st.button("Guardar presupuesto"):
        if limite > 0:
            guardar_presupuesto(cat_presupuesto, limite)
            st.success(f"Presupuesto de ${limite:,.0f} guardado para {cat_presupuesto}")
            st.rerun()
        else:
            st.warning("Ingresa un límite mayor a 0")

    df_pres = obtener_presupuestos()
    if not df_pres.empty:
        st.dataframe(df_pres, use_container_width=True)