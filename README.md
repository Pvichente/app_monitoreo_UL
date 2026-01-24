# 🎓 Instrumento de Monitoreo de Clases (Web App)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![Status](https://img.shields.io/badge/Status-MVP-green.svg)

Una aplicación web diseñada para optimizar la observación institucional en aulas universitarias. Esta herramienta permite a los **Course Managers** registrar métricas académicas en tiempo real, minimizando la carga cognitiva y sustituyendo el uso de papel u hojas de cálculo desconectadas.

## 🎯 Objetivo del Proyecto

Transformar la observación cualitativa en **datos cuantitativos estructurados** para su posterior análisis en Dashboards de Business Intelligence. El foco principal es la medición precisa del **Teacher Talk Time** (Tiempo de habla del facilitador) y la asistencia logística.

## 🚀 Características Principales

* **⏱️ Cronómetro de "Talk Time":** Algoritmo acumulativo que permite medir interacciones intermitentes y calcular el porcentaje de habla del profesor vs. tiempo total de clase.
* **🔐 Autenticación Simplificada:** Sistema de login basado en roles predefinidos para observadores autorizados.
* **⚡ Interfaz de Baja Fricción:** Diseño de "Tablero de Control" (Dashboard Layout) optimizado para laptops, permitiendo capturar datos sin perder de vista el aula.
* **💾 Persistencia de Sesión:** Uso de `st.session_state` para asegurar que ningún dato se pierda si el navegador se recarga accidentalmente.
* **📂 Simulación de Base de Datos:** Carga dinámica de cursos, grupos y facilitadores basada en el trimestre seleccionado.

## 🛠️ Stack Tecnológico

* **Lenguaje:** Python
* **Frontend/Backend:** Streamlit
* **Manejo de Datos:** Pandas
* **Lógica:** Session State & Datetime

## 💻 Instalación y Uso Local

Sigue estos pasos para ejecutar la aplicación en tu computadora:

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU-USUARIO/NOMBRE-DEL-REPO.git](https://github.com/TU-USUARIO/NOMBRE-DEL-REPO.git)
    cd NOMBRE-DEL-REPO
    ```

2.  **Crear un entorno virtual (Opcional pero recomendado):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3.  **Instalar las dependencias:**
    ```bash
    pip install streamlit pandas
    ```

4.  **Ejecutar la aplicación:**
    ```bash
    streamlit run app.py
    ```

## 📊 Estructura de Datos (Output)

Al finalizar una observación, la aplicación genera un objeto JSON con la siguiente estructura, listo para integración:

```json
{
  "meta": { "facilitador": "Dr. Roberto Casas", "grupo": "G-01" },
  "metrics": {
    "talk_time_sec": 3240,
    "talk_time_percentage": 60,
    "asistencia_temprana": 25,
    "inicio_puntual": true
  },
  "notas": "Observaciones cualitativas..."
}
