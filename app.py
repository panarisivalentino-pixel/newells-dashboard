"""
Dashboard · Newell's Old Boys 2000–2026: mercado de pases y rendimiento
Proyecto personal de portafolio — Valentino Panarisi (Tecnicatura en Ciencia de Datos e IA, UGR)

Cómo correrlo en tu compu:   streamlit run app.py
Los datos salen de los notebooks 01–04 (carpeta datos/).
"""
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------- configuración
st.set_page_config(page_title="Newell's · Mercado de pases 2000–2026", page_icon="🔴", layout="wide")
ROJO, NEGRO, GRIS, GRIS_CLARO = '#C8102E', '#1a1a1a', '#9e9e9e', '#e9e9e9'
COLOR_ARQ = {'Consolidado de alto valor': ROJO, 'Veterano que llega libre': NEGRO, 'Trotamundos experimentado': '#2c7fb8',
             'Joven a préstamo de club grande': '#f28e2b', 'Apuesta barata': '#59a14f'}
ORDEN_ARQ = list(COLOR_ARQ)
POSICIONES = ['Arquero', 'Defensor', 'Mediocampista', 'Delantero']
ANIO_COB = 2015            # desde acá los montos de compras y ventas tienen buena cobertura
ANIO_RATING = 2016         # primer año con puntajes de Sofascore
DATOS = Path(__file__).parent / 'datos' if (Path(__file__).parent / 'datos').exists() else Path(__file__).parent


def musd(v):
    """Formatea un monto en millones de USD."""
    return '—' if pd.isna(v) else f'{v / 1e6:,.1f} M'.replace(',', 'X').replace('.', ',').replace('X', '.')


def estilo(fig, alto=380):
    fig.update_layout(template='simple_white', height=alto, margin=dict(l=10, r=10, t=50, b=10),
                      font=dict(family='Inter, Arial', size=12), legend=dict(orientation='h', y=-0.15),
                      title_font=dict(size=15))
    return fig


# ---------------------------------------------------------------- carga de datos
@st.cache_data
def cargar():
    t = pd.read_csv(DATOS / 'transferencias.csv', parse_dates=['fecha'])
    t['con_monto'] = t.monto_final_usd.notna()      # el archivo ya trae solo los pases con monto conocido
    jug = pd.read_csv(DATOS / 'jugadores.csv')
    fich = pd.read_csv(DATOS / 'fichajes_etiquetados.csv')
    arq = pd.read_csv(DATOS / 'fichajes_arquetipos.csv')
    pred = pd.read_csv(DATOS / 'prediccion_en_curso.csv')
    met = pd.read_csv(DATOS / 'metricas_modelo.csv')
    cob = pd.read_csv(DATOS / 'cobertura_montos.csv')
    t = t.merge(jug[['tm_id', 'como_llego', 'grupo_posicion']], on='tm_id', how='left')
    return t, jug, fich, arq, pred, met, cob


t, jug, fich, arq, pred, met, cob = cargar()

# ---------------------------------------------------------------- barra lateral (filtros)
st.sidebar.markdown("## 🔴⚫ Filtros")
anios_con_datos = sorted(t[t.con_monto].anio.dropna().astype(int).unique())
desde, hasta = st.sidebar.select_slider('Período (año del pase)', options=anios_con_datos,
                                        value=(ANIO_COB, max(anios_con_datos)))
if desde < ANIO_COB:
    st.sidebar.warning(f'Antes de {ANIO_COB} casi no se publicaban los montos de compras: '
                       'los totales de esos años están incompletos.')
posiciones = st.sidebar.multiselect('Posición', POSICIONES, default=POSICIONES)
st.sidebar.caption('El período se aplica a plata, compras/ventas y buen fichaje. '
                   'La posición, a rendimiento, buen fichaje y arquetipos.')
st.sidebar.divider()
st.sidebar.markdown("**Fuentes:** Gonzalo Calvigioni (prioridad en montos), Transfermarkt, Sofascore, ESPN, "
                    "La Capital y club. Montos en USD.")
st.sidebar.markdown("Proyecto de **Valentino Panarisi** · Tecnicatura en Ciencia de Datos e IA (UGR)")

tp = t[t.anio.between(desde, hasta)]
ventas = tp[(tp.tipo_mov == 'baja') & tp.con_monto]
compras = tp[(tp.tipo_mov == 'alta') & tp.con_monto]

# ---------------------------------------------------------------- encabezado + KPIs
st.title("Newell's Old Boys · Mercado de pases y rendimiento")
st.caption(f'Período seleccionado: **{desde}–{hasta}** · Montos en dólares (USD) · '
           'Un monto no informado no se cuenta como 0: queda afuera de los totales.')

ingresos, egresos = ventas.monto_final_usd.sum(), compras.monto_final_usd.sum()
venta_max = ventas.loc[ventas.monto_final_usd.idxmax()] if len(ventas) else None
fe = fich[fich.evaluable & fich.anio.between(desde, hasta)]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric('Ingresos por ventas', musd(ingresos), f'{len(ventas)} ventas con monto', delta_color='off', delta_arrow='off')
k2.metric('Gasto en compras', musd(egresos), f'{len(compras)} compras con monto', delta_color='off', delta_arrow='off')
k3.metric('Saldo', musd(ingresos - egresos), 'positivo' if ingresos >= egresos else 'negativo',
          delta_color='normal' if ingresos >= egresos else 'inverse', delta_arrow='off')
k4.metric('Venta récord', musd(venta_max.monto_final_usd) if venta_max is not None else '—',
          f'{venta_max.jugador} ({int(venta_max.anio)})' if venta_max is not None else '', delta_color='off', delta_arrow='off')
k5.metric('Buenos fichajes', f'{fe.buen_fichaje.mean():.0%}' if len(fe) else '—', f'de {len(fe)} evaluados', delta_color='off', delta_arrow='off')

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(['💰 Plata por año y mes', '🔁 Compras y ventas', '📊 Rendimiento',
                                              '✅ ¿Buen fichaje?', '🧩 Arquetipos y modelo', 'ℹ️ Fuentes y método'])

# ================================================================ P1 · PLATA
with tab1:
    st.subheader('¿Cuánta plata entró y salió por transferencias?')
    st.caption(f'Período: {desde}–{hasta}. Cobertura buena de montos desde {ANIO_COB}; los años anteriores aparecen sombreados.')
    anual = (tp[tp.con_monto].pivot_table(index='anio', columns='tipo_mov', values='monto_final_usd', aggfunc='sum')
             .reindex(range(desde, hasta + 1)).fillna(0).rename(columns={'baja': 'ingresos', 'alta': 'egresos'}))
    for c in ('ingresos', 'egresos'):
        if c not in anual: anual[c] = 0.0
    anual['saldo'] = anual.ingresos - anual.egresos
    c1, c2 = st.columns([1.6, 1])
    fig = go.Figure()
    fig.add_bar(x=anual.index, y=anual.ingresos / 1e6, name='Ingresos (ventas)', marker_color=ROJO)
    fig.add_bar(x=anual.index, y=-anual.egresos / 1e6, name='Egresos (compras)', marker_color=NEGRO)
    fig.add_scatter(x=anual.index, y=anual.saldo / 1e6, name='Saldo', mode='lines+markers', line=dict(color=GRIS, dash='dot'))
    if desde < ANIO_COB:
        fig.add_vrect(x0=desde - 0.5, x1=min(ANIO_COB, hasta + 1) - 0.5, fillcolor=GRIS, opacity=0.12, line_width=0,
                      annotation_text='cobertura baja', annotation_position='top left')
    fig.update_layout(barmode='relative', yaxis_title='millones de USD', title='Ingresos y egresos por año')
    c1.plotly_chart(estilo(fig, 420), width='stretch')

    acum = anual.saldo.cumsum() / 1e6
    fig = px.area(x=acum.index, y=acum.values, labels={'x': '', 'y': 'millones de USD'}, title=f'Saldo acumulado desde {desde}')
    fig.update_traces(line_color=ROJO, fillcolor='rgba(200,16,46,0.15)')
    c2.plotly_chart(estilo(fig, 420), width='stretch')

    c1, c2 = st.columns([1.6, 1])
    tp_m = tp[tp.con_monto].assign(flujo=lambda d: np.where(d.tipo_mov == 'baja', d.monto_final_usd, -d.monto_final_usd))
    mapa = tp_m.pivot_table(index='anio', columns='mes', values='flujo', aggfunc='sum').reindex(columns=range(1, 13)) / 1e6
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    lim = np.nanmax(np.abs(mapa.values)) if mapa.size else 1
    fig = px.imshow(mapa.values, x=meses, y=[str(int(a)) for a in mapa.index], color_continuous_scale=[[0, NEGRO], [0.5, '#f7f7f7'], [1, ROJO]],
                    zmin=-lim, zmax=lim, text_auto='.1f', aspect='auto', title='Saldo por mes (M USD): rojo = entró, negro = salió')
    fig.update_coloraxes(showscale=False)
    c1.plotly_chart(estilo(fig, 420), width='stretch')
    por_mes = tp_m[tp_m.tipo_mov == 'baja'].groupby('mes').monto_final_usd.sum().reindex(range(1, 13)).fillna(0)
    fig = px.bar(x=meses, y=por_mes.values / 1e6, title='Ingresos por mes del año (todo el período)', labels={'x': '', 'y': 'millones de USD'})
    fig.update_traces(marker_color=[ROJO if m in (1, 7) else GRIS for m in range(1, 13)])
    c2.plotly_chart(estilo(fig, 420), width='stretch')
    if por_mes.sum() > 0:
        st.info(f'**Julio** concentra el {por_mes[7] / por_mes.sum():.0%} y **enero** el {por_mes[1] / por_mes.sum():.0%} de los ingresos '
                'del período: las dos ventanas de pases.')

# ================================================================ P2 · COMPRAS Y VENTAS
with tab2:
    st.subheader('¿Qué jugadores se vendieron y compraron, y con qué margen?')
    st.caption(f'Período: {desde}–{hasta}. Solo operaciones con monto conocido.')
    c1, c2 = st.columns([1.4, 1])
    top = ventas.sort_values('monto_final_usd', ascending=False).head(15).iloc[::-1]
    origen = top.como_llego.map(lambda c: 'Canterano' if c in ('canterano', 'ya_estaba_en_1999') else 'Llegó de otro club')
    fig = px.bar(top, x=top.monto_final_usd / 1e6, y=top.jugador + ' (' + top.anio.astype(int).astype(str) + ')', orientation='h',
                 color=origen, color_discrete_map={'Canterano': ROJO, 'Llegó de otro club': NEGRO},
                 hover_data={'club_contraparte': True, 'fuente_final': True}, title='Top 15 ventas',
                 labels={'x': 'millones de USD', 'y': '', 'color': ''})
    c1.plotly_chart(estilo(fig, 480), width='stretch')

    v = ventas.assign(origen=ventas.como_llego.map(lambda c: 'Canteranos' if c in ('canterano', 'ya_estaba_en_1999')
                                                    else 'Comprados' if c in ('comprado', 'comprado_sin_monto') else 'Libres / préstamos'))
    g = v.groupby('origen').monto_final_usd.agg(['sum', 'count', 'median']).reset_index()
    fig = px.pie(g, names='origen', values='sum', hole=0.55, title='¿De dónde sale la plata de las ventas?',
                 color='origen', color_discrete_map={'Canteranos': ROJO, 'Comprados': NEGRO, 'Libres / préstamos': GRIS})
    fig.update_traces(textinfo='percent+label', showlegend=False)
    c2.plotly_chart(estilo(fig, 330), width='stretch')
    c2.dataframe(g.rename(columns={'origen': 'Origen', 'sum': 'Total (M)', 'count': 'Ventas', 'median': 'Mediana (M)'})
                 .assign(**{'Total (M)': lambda d: (d['Total (M)'] / 1e6).round(1), 'Mediana (M)': lambda d: (d['Mediana (M)'] / 1e6).round(2)}),
                 hide_index=True, width='stretch')

    st.markdown('#### Margen por jugador (venta − compra)')
    st.caption('Para canteranos y libres el costo es 0 (más préstamos pagados, si los hubo). Período de la **última salida** del jugador.')
    mj = jug[jug.margen_usd.notna()].copy()
    mj['anio_salida'] = pd.to_datetime(mj.ultima_salida, errors='coerce').dt.year
    mj = mj[mj.anio_salida.between(desde, hasta)]
    c1, c2 = st.columns([1, 1.2])
    cmp = mj[mj.como_llego == 'comprado']
    fig = px.scatter(cmp, x='compra_usd', y='venta_usd', text='jugador', log_x=True, log_y=True,
                     title='Jugadores comprados: precio de compra vs. de venta', labels={'compra_usd': 'compra (USD)', 'venta_usd': 'venta (USD)'},
                     color=np.where(cmp.margen_usd > 0, 'ganancia', 'pérdida'), color_discrete_map={'ganancia': ROJO, 'pérdida': NEGRO})
    if len(cmp):
        lo, hi = cmp[['compra_usd', 'venta_usd']].min().min() * 0.7, cmp[['compra_usd', 'venta_usd']].max().max() * 1.4
        fig.add_scatter(x=[lo, hi], y=[lo, hi], mode='lines', line=dict(color=GRIS, dash='dash'), name='equilibrio')
    fig.update_traces(textposition='top center', textfont_size=9, selector=dict(mode='markers+text'))
    c1.plotly_chart(estilo(fig, 420), width='stretch')
    c2.dataframe(mj.sort_values('margen_usd', ascending=False)[['jugador', 'como_llego', 'grupo_posicion', 'compra_usd', 'venta_usd', 'margen_usd']]
                 .rename(columns={'como_llego': 'cómo llegó', 'grupo_posicion': 'posición', 'compra_usd': 'compra', 'venta_usd': 'venta', 'margen_usd': 'margen'}),
                 hide_index=True, width='stretch', height=420,
                 column_config={c: st.column_config.NumberColumn(format='$%.0f') for c in ['compra', 'venta', 'margen']})

# ================================================================ P3 · RENDIMIENTO
with tab3:
    st.subheader('¿Qué rendimiento tuvo cada jugador?')
    st.caption('Estadísticas: Transfermarkt, temporadas 2000–2026 (acumulado en Newell\'s). Puntajes: Sofascore, desde 2016, partidos oficiales.')
    jp = jug[jug.grupo_posicion.isin(posiciones) & jug.minutos.notna()]
    c1, c2 = st.columns(2)
    min_min = c1.slider('Mínimo de minutos jugados (para G+A/90)', 450, 5000, 900, step=50)
    min_rat = c2.slider('Mínimo de partidos con puntaje (para rating)', 5, 100, 20, step=5)

    c1, c2 = st.columns(2)
    of = jp[jp.grupo_posicion.isin(['Delantero', 'Mediocampista']) & (jp.minutos >= min_min)].copy()
    of['goles/90'] = of.goles / of.minutos * 90; of['asist./90'] = of.asistencias / of.minutos * 90
    t15 = of.sort_values('g_a_por90', ascending=False).head(15).iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=t15.jugador, x=t15['goles/90'], orientation='h', name='goles / 90', marker_color=ROJO)
    fig.add_bar(y=t15.jugador, x=t15['asist./90'], orientation='h', name='asistencias / 90', marker_color=NEGRO)
    fig.update_layout(barmode='stack', title=f"Atacantes y medios: G+A cada 90' (mín. {min_min} min)")
    c1.plotly_chart(estilo(fig, 480), width='stretch')

    r = jp[jp.partidos_con_rating >= min_rat].sort_values('rating_promedio', ascending=False).head(15).iloc[::-1]
    fig = px.bar(r, x='rating_promedio', y=r.jugador + ' (' + r.partidos_con_rating.astype(int).astype(str) + ')', orientation='h',
                 color='grupo_posicion', color_discrete_map={'Arquero': NEGRO, 'Defensor': ROJO, 'Mediocampista': '#2c7fb8', 'Delantero': GRIS},
                 title=f'Mejor puntaje promedio Sofascore (mín. {min_rat} partidos)', labels={'y': '', 'rating_promedio': 'rating', 'grupo_posicion': ''})
    fig.update_yaxes(categoryorder='total ascending')
    fig.update_xaxes(range=[6.4, max(7.6, r.rating_promedio.max() + 0.05) if len(r) else 7.6])
    c2.plotly_chart(estilo(fig, 480), width='stretch')

    c1, c2 = st.columns(2)
    de = jp[jp.grupo_posicion.isin(['Defensor', 'Arquero'])].sort_values('partidos', ascending=False).head(12).iloc[::-1]
    fig = px.bar(de, x='partidos', y='jugador', orientation='h', color='grupo_posicion', color_discrete_map={'Defensor': ROJO, 'Arquero': NEGRO},
                 title='Defensores y arqueros con más partidos', labels={'jugador': '', 'grupo_posicion': ''})
    c1.plotly_chart(estilo(fig, 420), width='stretch')
    ar = jug[(jug.grupo_posicion == 'Arquero') & (jug.partidos_con_rating >= 10)].assign(pct=lambda d: d.vallas_invictas / d.partidos_con_rating * 100)
    ar = ar.sort_values('pct')
    fig = px.bar(ar, x='pct', y='jugador', orientation='h', text=ar.vallas_invictas.astype(int).astype(str) + ' vallas',
                 title=f'Arqueros: % de partidos con valla invicta (desde {ANIO_RATING}, mín. 10)', labels={'pct': '%', 'jugador': ''})
    fig.update_traces(marker_color=NEGRO, textposition='outside')
    c2.plotly_chart(estilo(fig, 420), width='stretch')

    st.markdown('#### Tabla de jugadores')
    buscar = st.text_input('Buscar jugador', '')
    tabla = jp if not buscar else jp[jp.jugador.str.contains(buscar, case=False, na=False)]
    st.dataframe(tabla.sort_values('minutos', ascending=False)[['jugador', 'grupo_posicion', 'como_llego', 'temporadas', 'partidos', 'minutos', 'goles',
                                                                 'asistencias', 'g_a_por90', 'partidos_con_rating', 'rating_promedio', 'vallas_invictas']],
                 hide_index=True, width='stretch', height=380,
                 column_config={'g_a_por90': st.column_config.NumberColumn('G+A/90', format='%.2f'),
                                'rating_promedio': st.column_config.NumberColumn('rating', format='%.2f')})

# ================================================================ P4 · BUEN FICHAJE
with tab4:
    st.subheader('¿Fue un buen fichaje?')
    with st.expander('Criterio usado (definido en el Notebook 02)', expanded=False):
        st.markdown("""
**Buen fichaje = Participación Y (Contribución O Resultado económico)**
- **Participación:** jugó en promedio ≥ 1000 minutos por temporada.
- **Contribución:** delanteros y medios con G+A/90 ≥ percentil 40 de su grupo; defensores y arqueros con rating ≥ mediana de su grupo (o ≥ 1800 min/temporada si no hay rating).
- **Económico:** se vendió por más de lo que costó.

Se evalúan los fichajes no canteranos que llegaron hasta junio de 2025.
""")
    fp = fich[fich.evaluable & fich.anio.between(desde, hasta) & fich.grupo_posicion.isin(posiciones)].copy()
    st.caption(f'Período: {desde}–{hasta} · {len(fp)} fichajes evaluados (año de llegada).')
    if len(fp):
        c1, c2 = st.columns(2)
        por_anio = fp.groupby(fp.anio.astype(int)).buen_fichaje.agg(['mean', 'count']).reset_index()
        fig = px.bar(por_anio, x='anio', y=por_anio['mean'] * 100, text=por_anio['count'].map(lambda n: f'n={n}'),
                     title='% de buenos fichajes por año de llegada', labels={'y': '%', 'anio': ''})
        fig.update_traces(marker_color=ROJO, textposition='outside', textfont_size=9)
        fig.add_hline(y=fp.buen_fichaje.mean() * 100, line_dash='dash', line_color=GRIS, annotation_text='promedio')
        c1.plotly_chart(estilo(fig, 380), width='stretch')
        pos = fp.groupby('grupo_posicion').buen_fichaje.agg(['mean', 'count']).reindex(POSICIONES).dropna().reset_index()
        fig = px.bar(pos, x='grupo_posicion', y=pos['mean'] * 100, text=pos.apply(lambda r: f"{r['mean']:.0%} (n={int(r['count'])})", axis=1),
                     title='% de buenos fichajes por posición', labels={'y': '%', 'grupo_posicion': ''})
        fig.update_traces(marker_color=NEGRO, textposition='outside')
        c2.plotly_chart(estilo(fig, 380), width='stretch')
        st.dataframe(fp.sort_values(['buen_fichaje', 'min_por_temp'], ascending=False)[
            ['jugador', 'anio', 'categoria', 'grupo_posicion', 'temporadas', 'min_por_temp', 'ga90', 'rating', 'participacion', 'contribucion', 'economico', 'buen_fichaje']]
            .assign(buen_fichaje=lambda d: d.buen_fichaje.map({1.0: '✅ bueno', 0.0: '❌ no'})),
            hide_index=True, width='stretch', height=400,
            column_config={'anio': st.column_config.NumberColumn('año', format='%d'), 'min_por_temp': st.column_config.NumberColumn('min/temp', format='%.0f'),
                           'ga90': st.column_config.NumberColumn('G+A/90', format='%.2f'), 'rating': st.column_config.NumberColumn(format='%.2f')})
    else:
        st.warning('No hay fichajes evaluados con estos filtros.')

# ================================================================ ARQUETIPOS + MODELO
with tab5:
    st.subheader('Arquetipos de fichaje (clustering) y probabilidad de éxito (modelo)')
    st.caption('Clustering K-Means sobre el perfil al llegar (edad, valor de mercado, clubes previos, origen, tipo de operación). '
               'Solo fichajes con valor de mercado conocido: en la práctica 2010–2026.')
    ap = arq[arq.grupo_posicion.isin(posiciones)]
    c1, c2 = st.columns([1.3, 1])
    fig = px.scatter(ap, x='PC1', y='PC2', color='arquetipo', category_orders={'arquetipo': ORDEN_ARQ}, color_discrete_map=COLOR_ARQ,
                     hover_name='jugador', hover_data={'anio': True, 'edad_llegada': True, 'club_contraparte': True, 'PC1': False, 'PC2': False},
                     title='Mapa de fichajes (PCA): → más experiencia, ↑ más valor de mercado',
                     labels={'PC1': 'experiencia (edad + clubes previos)', 'PC2': 'valor de mercado'})
    fig.update_traces(marker=dict(size=9, line=dict(width=0.5, color='white')))
    c1.plotly_chart(estilo(fig, 480), width='stretch')
    ev = ap[ap.evaluable].groupby('arquetipo').agg(pct=('buen_fichaje', 'mean'), n=('buen_fichaje', 'size')).reindex(ORDEN_ARQ).dropna().reset_index()
    fig = px.bar(ev, y='arquetipo', x=ev.pct * 100, orientation='h', color='arquetipo', color_discrete_map=COLOR_ARQ,
                 text=ev.apply(lambda r: f"{r.pct:.0%} (n={int(r.n)})", axis=1), title='% de buenos fichajes por arquetipo',
                 labels={'x': '%', 'arquetipo': ''})
    fig.update_traces(textposition='outside', cliponaxis=False); fig.update_layout(showlegend=False, xaxis_range=[0, 100])
    fig.update_yaxes(categoryorder='array', categoryarray=ORDEN_ARQ[::-1])
    c2.plotly_chart(estilo(fig, 480), width='stretch')

    st.markdown('#### Fichajes en curso (desde julio de 2025)')
    st.caption('**Arquetipo** y su tasa histórica (Notebook 04) + **probabilidad** de la regresión logística (Notebook 03). '
               'Son estimaciones orientativas: el modelo tiene AUC ≈ 0,65 en test.')
    curso = pred.merge(arq[['jugador', 'anio', 'arquetipo']], on=['jugador', 'anio'], how='left')
    tasa_arq = arq[arq.evaluable].groupby('arquetipo').buen_fichaje.mean()
    curso['tasa_arquetipo'] = curso.arquetipo.map(tasa_arq) * 100
    curso['prob_buen_fichaje'] = curso.prob_buen_fichaje * 100
    curso = curso[curso.grupo_posicion.isin(posiciones)].sort_values('prob_buen_fichaje', ascending=False)
    st.dataframe(curso[['jugador', 'grupo_posicion', 'edad_llegada', 'tipo_operacion', 'club_contraparte', 'valor_mercado_usd', 'arquetipo', 'tasa_arquetipo', 'prob_buen_fichaje']],
                 hide_index=True, width='stretch',
                 column_config={'valor_mercado_usd': st.column_config.NumberColumn('valor de mercado', format='$%.0f'),
                                'tasa_arquetipo': st.column_config.ProgressColumn('% éxito del arquetipo', format='%.0f%%', min_value=0, max_value=100),
                                'prob_buen_fichaje': st.column_config.ProgressColumn('prob. modelo', format='%.0f%%', min_value=0, max_value=100)})
    with st.expander('Métricas del modelo supervisado (test 2019–2025)'):
        st.dataframe(met.round(3), hide_index=True, width='stretch')
        st.markdown('El modelo se eligió por validación cruzada (regresión logística). Sirve para **ordenar** fichajes por chances, no para decidir con certeza.')

# ================================================================ FUENTES Y MÉTODO
with tab6:
    st.subheader('Fuentes, método y limitaciones')
    st.markdown("""
**Fuentes de datos**
| Dato | Fuente | Período |
|---|---|---|
| Montos de transferencias | **Gonzalo Calvigioni** (prioridad) · club · La Capital · Transfermarkt | 2000–2026 |
| Altas, bajas, valor de mercado, estadísticas por temporada | Transfermarkt | 2000–2026 |
| Puntaje por partido | Sofascore | 2016–2026 |
| Contraste de estadísticas | ESPN | 2003–2026 |

**Regla del monto final:** Calvigioni > club oficial > consenso de ≥ 2 fuentes (dentro de un 20%) > La Capital > Transfermarkt. Montos en euros convertidos a USD con el tipo de cambio de la fecha del pase.

**Notebooks del proyecto:** 01 obtención y preparación · 02 análisis exploratorio · 03 supervisado (¿se puede predecir un buen fichaje?) · 04 no supervisado (arquetipos).
""")
    st.markdown('**Cobertura de montos por temporada** (por eso el período por defecto arranca en 2015)')
    fig = go.Figure()
    fig.add_bar(x=cob.temporada_inicio, y=cob['% compras con monto'], name='% compras con monto', marker_color=NEGRO)
    fig.add_bar(x=cob.temporada_inicio, y=cob['% ventas con monto'], name='% ventas con monto', marker_color=ROJO)
    fig.add_vline(x=ANIO_COB - 0.5, line_dash='dash', line_color=GRIS)
    st.plotly_chart(estilo(fig, 320), width='stretch')
    st.markdown("""
**Limitaciones**
- Antes de 2015 la mayoría de las compras no tienen monto publicado: los totales de esos años están incompletos.
- Los márgenes de jugadores comprados se apoyan en pocos casos.
- El criterio de "buen fichaje" es una definición del proyecto; otros umbrales cambian los porcentajes.
- Los arquetipos no están muy separados entre sí (silueta 0,17): son tendencias, no cajas cerradas.
""")
