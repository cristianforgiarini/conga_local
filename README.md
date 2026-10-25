# Conga local (Tuya)

Integración para Home Assistant que controla la aspiradora **Cecotec Conga 8290** en red local,
con su perfil completo, y muestra el mapa con la ruta de la última limpieza.

Es una copia adaptada de [Tuya Local](https://github.com/make-all/tuya-local) (MIT), con el perfil de
la Conga incluido y el mapa como única parte que usa la nube de Tuya.

## Qué hace

- **Todo en local:** estado, batería, fallos, modos, selector de habitaciones y el resto de entidades
  del perfil. Se comunica con el robot por la red local, sin nube.
- **Selector de habitaciones:** elige una habitación o tu plan completo, con una o dos pasadas,
  desde el dashboard o una automatización.
- **Mapa:** imagen con habitaciones, paredes, la ruta de la última limpieza y la posición final.
  Se actualiza cada hora desde la nube de Tuya.

## Qué no hace

- **No hay posición en directo.** La ruta es la de la última limpieza guardada por Tuya.
- **No es un producto de Tuya ni tiene su soporte.** Usa APIs no documentadas para el mapa.

## Requisitos

- Home Assistant 2026.8 o superior.
- El robot en la red local y su **clave local** (la obtienes con Tuya Local o con la herramienta
  [tinytuya](https://github.com/jasonacox/tinytuya)).
- Para el mapa: un **Client ID** y **Client Secret** de la plataforma de desarrolladores de Tuya,
  con acceso a la API de aspiradoras. Solo se usan para descargar el mapa.

## Instalación con HACS

1. En HACS, menú de los tres puntos → **Repositorios personalizados**.
2. Añade la URL de este repositorio y elige la categoría **Integración**.
3. Busca "Conga local (Tuya)" e instálala.
4. Reinicia Home Assistant.
5. Ajustes → Dispositivos y servicios → Añadir integración → **Conga local (Tuya)** → configuración manual,
   con la IP, la clave local y el ID del dispositivo.

## Atribución

Código base: Tuya Local, © 2018 Nik Rolls, 2026 Jason Rumney y colaboradores. Licencia MIT, incluida en
`LICENSE` y en `custom_components/conga_local/LICENSE_TUYA_LOCAL.md`.

## Aviso

Proyecto personal, sin garantía, como indica la licencia. Usa tu propio robot y tus propias credenciales.
