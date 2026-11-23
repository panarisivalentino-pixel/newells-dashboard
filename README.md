# Newell's Old Boys 2000–2026 · Mercado de pases y rendimiento

Dashboard interactivo (Streamlit) del proyecto personal de **Valentino Panarisi** — Tecnicatura en Ciencia de Datos e IA (UGR).

**Preguntas que responde**
1. ¿Cuánta plata entró y salió por transferencias, por mes y por año?
2. ¿Qué jugadores se compraron y vendieron, a qué precio y con qué margen? (canteranos vs fichajes)
3. ¿Qué rendimiento tuvo cada jugador? (G+A/90, partidos, vallas invictas, puntaje Sofascore)
4. ¿Fue un buen fichaje? + arquetipos de fichaje (clustering) y probabilidad de éxito (modelo supervisado)

**Fuentes:** Gonzalo Calvigioni (prioridad en montos), Transfermarkt, Sofascore, ESPN, La Capital y el club. Montos en USD.

**Correr en tu compu**
```
pip install -r requirements.txt
streamlit run app.py
```

Los datos de `datos/` salen de los notebooks 01–04 del proyecto (Google Colab).
