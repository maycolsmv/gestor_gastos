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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metas_ahorro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            objetivo REAL,
            fecha_limite TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aportes_ahorro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_id INTEGER,
            monto REAL,
            nota TEXT,
            fecha TEXT,
            FOREIGN KEY (meta_id) REFERENCES metas_ahorro(id)
        )
    ''')
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

def crear_meta(nombre, objetivo, fecha_limite):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO metas_ahorro (nombre, objetivo, fecha_limite) VALUES (?, ?, ?)",
                   (nombre, objetivo, fecha_limite))
    conn.commit()
    conn.close()

def obtener_metas():
    conn = sqlite3.connect("data/gastos.db")
    df = pd.read_sql_query("SELECT * FROM metas_ahorro", conn)
    conn.close()
    return df

def agregar_aporte(meta_id, monto, nota):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO aportes_ahorro (meta_id, monto, nota, fecha) VALUES (?, ?, ?, ?)",
                   (meta_id, monto, nota, fecha))
    conn.commit()
    conn.close()

def obtener_total_aportado(meta_id):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(monto) FROM aportes_ahorro WHERE meta_id=?", (meta_id,))
    total = cursor.fetchone()[0] or 0
    conn.close()
    return total

def obtener_aportes_meta(meta_id):
    conn = sqlite3.connect("data/gastos.db")
    df = pd.read_sql_query("""
        SELECT fecha, monto, nota FROM aportes_ahorro 
        WHERE meta_id=? ORDER BY fecha
    """, conn, params=(meta_id,))
    conn.close()
    return df

def eliminar_meta(meta_id):
    conn = sqlite3.connect("data/gastos.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM aportes_ahorro WHERE meta_id=?", (meta_id,))
    cursor.execute("DELETE FROM metas_ahorro WHERE id=?", (meta_id,))
    conn.commit()
    conn.close()

# ── Inicializar ──
os.makedirs("data", exist_ok=True)
init_db()

METODOS_PAGO = ["Efectivo", "Tarjeta débito", "Tarjeta crédito", "Nequi", "Daviplata", "Transferencia", "Otro"]

# ── UI ──
st.title("💰 Gestor de Gastos")

st.markdown("""
    <style>
        /* Fondo principal */
        .stApp {
            background-color: #0e1117;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1a1f2e;
            border-right: 2px solid #3498db;
        }
        
        /* Título principal */
        h1 {
            color: #3498db;
            font-weight: 800;
            letter-spacing: 1px;
        }
        
        /* Subtítulos */
        h2, h3 {
            color: #ffffff;
            border-bottom: 1px solid #3498db;
            padding-bottom: 5px;
        }
        
        /* Botones */
        .stButton > button {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 600;
            transition: 0.3s;
        }
        
        .stButton > button:hover {
            background-color: #2980b9;
            transform: scale(1.02);
        }

        /* Métricas */
        [data-testid="stMetric"] {
            background-color: #1a1f2e;
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #3498db;
        }

        /* Inputs */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {
            background-color: #1a1f2e;
            color: white;
            border: 1px solid #3498db;
            border-radius: 8px;
        }

        /* Selectbox */
        .stSelectbox > div > div {
            background-color: #1a1f2e;
            border: 1px solid #3498db;
            border-radius: 8px;
        }

        /* Expander */
        .streamlit-expanderHeader {
            background-color: #1a1f2e;
            border: 1px solid #3498db;
            border-radius: 8px;
        }

        /* Divider */
        hr {
            border-color: #3498db;
        }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("📋 Menú")
pagina = st.sidebar.radio("", ["➕ Agregar", "📊 Resumen", "📋 Historial", "🐷 Ahorro", "⚙️ Configuración"])

CATEGORIAS = obtener_categorias()

if pagina == "➕ Agregar":
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

elif pagina == "📊 Resumen":
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

elif pagina == "📋 Historial":
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

elif pagina == "🐷 Ahorro":
    st.subheader("🐷 Metas de Ahorro")

    with st.expander("➕ Crear nueva meta"):
        nombre_meta = st.text_input("Nombre de la meta (ej: Vacaciones):")
        objetivo_meta = st.number_input("Monto objetivo:", min_value=0.0, step=10000.0)
        fecha_limite_meta = st.date_input("Fecha límite:")
        if st.button("Crear meta"):
            if nombre_meta and objetivo_meta > 0:
                crear_meta(nombre_meta, objetivo_meta, str(fecha_limite_meta))
                st.success(f"Meta '{nombre_meta}' creada correctamente")
                st.rerun()
            else:
                st.warning("Completa todos los campos")

    df_metas = obtener_metas()
    if not df_metas.empty:
        for _, meta in df_metas.iterrows():
            total_aportado = obtener_total_aportado(meta["id"])
            objetivo = meta["objetivo"]
            porcentaje = min(total_aportado / objetivo, 1.0) if objetivo > 0 else 0

            with st.expander(f"🎯 {meta['nombre']} — ${total_aportado:,.0f} / ${objetivo:,.0f}"):
                if porcentaje >= 1.0:
                    st.success("🎉 ¡Meta alcanzada!")
                else:
                    st.write(f"📅 Fecha límite: {meta['fecha_limite']}")
                st.progress(porcentaje)
                st.write(f"**{porcentaje*100:.1f}%** completado")

                col1, col2 = st.columns(2)
                with col1:
                    monto_aporte = st.number_input("Aporte:", min_value=0.0, step=10000.0, key=f"aporte_{meta['id']}")
                with col2:
                    nota_aporte = st.text_input("Nota:", key=f"nota_{meta['id']}")
                if st.button("Agregar aporte", key=f"btn_{meta['id']}"):
                    if monto_aporte > 0:
                        agregar_aporte(meta["id"], monto_aporte, nota_aporte)
                        st.success(f"Aporte de ${monto_aporte:,.0f} agregado")
                        st.rerun()
                    else:
                        st.warning("Ingresa un monto")

                df_aportes = obtener_aportes_meta(meta["id"])
                if not df_aportes.empty:
                    df_aportes["acumulado"] = df_aportes["monto"].cumsum()
                    fig = px.line(df_aportes, x="fecha", y="acumulado", markers=True,
                                  title="Evolución del ahorro",
                                  color_discrete_sequence=["#2ecc71"])
                    fig.add_hline(y=objetivo, line_dash="dash", line_color="red",
                                  annotation_text="Objetivo")
                    st.plotly_chart(fig, use_container_width=True)

                if st.button("🗑️ Eliminar meta", key=f"del_{meta['id']}"):
                    eliminar_meta(meta["id"])
                    st.success("Meta eliminada")
                    st.rerun()
    else:
        st.info("No tienes metas de ahorro aún. ¡Crea una!")

elif pagina == "⚙️ Configuración":
    st.subheader("⚙️ Configuración")

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