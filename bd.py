import psycopg2
from psycopg2 import pool
import time
from datetime import datetime, timedelta
import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# PostgreSQL connection parameters
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": os.getenv("DB_PORT", "5432")
}

try:
    pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        **DB_CONFIG
    )
    logger.info("Pool de conexiones de PostgreSQL creado exitosamente.")
except psycopg2.Error as e:
    logger.critical(f"Error crítico al crear el pool de conexiones: {e}")
    raise

def get_db_connection():
    connection = None
    try:
        connection = pool.getconn()
        return connection
    except psycopg2.Error as e:
        logger.error(f"Error al obtener conexión de la piscina: {e}")
        raise
    finally:
        if connection:
            pool.putconn(connection)

def crear_tablas(connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monedas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(30) NOT NULL,
                UNIQUE (nombre)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fuentes (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL,
                UNIQUE (nombre)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bancos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(80) NOT NULL,
                UNIQUE (nombre)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS precios (
                id SERIAL PRIMARY KEY,
                fuente INT NOT NULL,
                moneda INT NOT NULL,
                precio DECIMAL(10,2) NOT NULL,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                CONSTRAINT fk_precios_moneda FOREIGN KEY (moneda) REFERENCES monedas(id),
                CONSTRAINT fk_precios_fuente FOREIGN KEY (fuente) REFERENCES fuentes(id),
                CONSTRAINT uq_precios UNIQUE (fuente, moneda, fecha, hora),
                KEY idx_precios_moneda (moneda),
                KEY idx_precios_fuente (fuente)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasa_informativa (
                id SERIAL PRIMARY KEY,
                fecha DATE NOT NULL,
                banco INT NOT NULL,
                compra DECIMAL(10,2) NOT NULL,
                venta  DECIMAL(10,2) NOT NULL,
                CONSTRAINT fk_tasa_banco FOREIGN KEY (banco) REFERENCES bancos(id),
                CONSTRAINT uq_tasa UNIQUE (banco, fecha)
            )
        """)

        cursor.execute("""
            CREATE OR REPLACE VIEW detalle_precios AS
            SELECT 
                p.precio,
                p.fecha,
                p.hora,
                f.nombre AS fuente,
                m.nombre AS moneda
            FROM precios p
            INNER JOIN fuentes  f ON p.fuente = f.id
            INNER JOIN monedas  m ON p.moneda = m.id
        """)

        cursor.executemany(
            """
            INSERT INTO monedas (nombre) 
            VALUES (%s)
            ON CONFLICT (nombre) DO NOTHING
            """,
            [("USD",), ("EUR",), ("TRY",), ("RUB",), ("CNY",)]
        )

        cursor.executemany(
            """
            INSERT INTO fuentes (nombre) 
            VALUES (%s)
            ON CONFLICT (nombre) DO NOTHING
            """,
            [("bcv",), ("c_d",), ("i_c",), ("e_m",)]
        )

        cursor.executemany(
            """
            INSERT INTO bancos (nombre) 
            VALUES (%s)
            ON CONFLICT (nombre) DO NOTHING
            """,
            [("Banesco",),("BBVA Provincial",),("Banco Mercantil",),("Banco Plaza",),
            ("Banco Exterior",),("Otras Instituciones",),("Banco de Venezuela",),
            ("Banco Nacional de Crédito BNC",),("Banco Activo",),("Bancamiga",),
            ("BanCaribe",),("Banplus",),("R4",)]
        )

        #connection.commit()
        logger.info("Tablas, vista y datos base creados/insertados correctamente")

    except psycopg2.Error as e:
        logger.error(f"Error en la creación de tablas: {e}")
        connection.rollback()
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def precio_ayer(fecha: str | None = None, moneda: str | None = None, fuente: str | None = None):
    connection = pool.get_connection()
    cursor = connection.cursor()

    if fecha:
        fecha = datetime.datetime.strptime(fecha, "%Y-%m-%d")
        fecha = fecha - timedelta(days=1)

    else:
        fecha = datetime.date.today() - timedelta(days=1)
        
    try:
        sql = "SELECT precio, fecha, hora FROM detalle_precios WHERE fecha = %s"
        params = [fecha]

        if moneda:
            sql += " AND moneda = %s"
            params.append(moneda)
        if fuente:
            sql += " AND fuente = %s"
            params.append(fuente)

        sql += " ORDER BY hora DESC LIMIT 1"

        cursor.execute(sql, params)
        result = cursor.fetchone()
        
        if result:
            result = list(result)
            result[0] = float(result[0])
            result[1] = str(result[1])
            return {"precio": float(result[0]), "fecha": str(result[1]), "hora": str(result[2])}
        else:
            logger.warning("No se encontraron datos para la fecha especificada.")
            return {"message": "No data found for the specified date"}
        
    except psycopg2.Error as e:
        logger.error(f"Error al consultar el precio para la fecha especificada: {e}")
        return {"error": f"Error en consulta: {str(e)}"}
    finally:
        cursor.close()
        connection.close()
        
def leer_usd(connection, fuente: str | None = None, fecha: str | None = None):
    cursor = connection.cursor() 

    if not fuente:
        fuente = "bcv"
        #logger.info("Fuente no especificada, se usará 'bcv' por defecto.")

    if not fecha:
        fecha = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        sql = "SELECT precio, fecha, hora, fuente FROM detalle_precios WHERE moneda = %s and fuente = %s"
        params = ["usd", fuente]
        
        if fecha:
            sql += " AND fecha = ?"
            params.append(fecha)

        fuentes = {"bcv": "bcv", "c_d": "criptodolar", "i_c": "italcambio"}
        
        sql += " ORDER BY fecha DESC, hora DESC LIMIT 1"
        
        cursor.execute(sql, params)
        result = cursor.fetchone()
        
        if result:
            precio_actual = float(result[0])
            fecha_actual = str(result[1])
            hora_actual = str(result[2])
            fuente_actual = str(result[3])

            precio_viejo = precio_ayer(fecha=fecha, moneda="usd", fuente=fuente)
            
            diferencia = None
            tendencia = None
            precio_anterior = None
            fecha_anterior = None
            hora_anterior = None
            
            if precio_viejo:
                precio_anterior = precio_viejo["precio"]
                fecha_anterior = precio_viejo["fecha"]
                hora_anterior = precio_viejo["hora"]
                diferencia = precio_actual - precio_anterior
                diferencia = round(diferencia, 2)
                
                if diferencia > 0:
                    tendencia = "increased"
                elif diferencia < 0:
                    tendencia = "decreased"
                else:
                    tendencia = "no changes"

            if fuente in fuentes:
                fuente_actual = fuentes[fuente]

            d = {
                "datetime" : datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                "currency": "usd",
                "data": {
                    "update_price": precio_actual,
                    "update_date": fecha_actual,
                    "update_time": hora_actual,
                    "source": fuente_actual,
                    "previous_price": precio_anterior,
                    "previous_date": fecha_anterior,
                    "previous_time": hora_anterior,
                    "difference": diferencia,
                    "trend": tendencia,
                }
            }
            
            #logger.info(f"Datos USD leídos: {d}")
            return d
        else:
            logger.warning(f"No se encontraron datos USD para fuente={fuente}, fecha={fecha}")
            return {"message": f"No USD data found for source={fuente}, date={fecha}"}
            
    except psycopg2.Error as e:
        logger.error(f"Error en la consulta de USD: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()

def precio_usd(fuente, moneda, valor, fecha, hora):
    conexion = None
    cursor = None

    try:
        conexion = pool.getconn()
        cursor = conexion.cursor()

        sql = "INSERT INTO precios(fuente, moneda, precio, fecha, hora) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(sql, (fuente, moneda, valor, fecha, hora))
        conexion.commit()
        logger.info(f"✅ Datos insertados: fuente={fuente}, moneda={moneda}, valor={valor}, fecha={fecha}, hora={hora}")
        
        return {"message": "Data inserted successfully"}

    except Exception as e:
        logger.error(f"Error al insertar datos: {e}")
        return {"error": f"Error inserting data: {str(e)}"}

    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()

def leer_eur(conexion, moneda, fuente: str | None = None, fecha: str | None = None):
    cursor = conexion.cursor() 

    if not fuente:
        fuente = "bcv"
        logger.info("Fuente no especificada, se usará 'bcv' por defecto.")

    try:
        sql = "SELECT precio, fecha, hora, fuente FROM detalle_precios WHERE moneda = %s and fuente = %s"
        params = [moneda, fuente]
        
        if fecha:
            sql += " AND fecha = ?"
            params.append(fecha)
        
        sql += " ORDER BY fecha DESC, hora DESC LIMIT 1"

        fuentes = {"bcv": "bcv", "c_d": "criptodolar", "i_c": "italcambio"}
        
        cursor.execute(sql, params)
        result = cursor.fetchone()

        if result:
            precio_actual = float(result[0])
            fecha_actual = str(result[1])
            hora_actual = str(result[2])
            fuente_actual = str(result[3])

            precio_viejo = precio_ayer(fecha=fecha, moneda=moneda, fuente=fuente)
            
            diferencia = None
            tendencia = None
            precio_anterior = None
            fecha_anterior = None
            hora_anterior = None
            
            if precio_viejo:
                precio_anterior = precio_viejo["precio"]
                fecha_anterior = precio_viejo["fecha"]
                hora_anterior = precio_viejo["hora"]
                diferencia = precio_actual - precio_anterior
                diferencia = round(diferencia, 2)
                
                if diferencia > 0:
                    tendencia = "increased"
                elif diferencia < 0:
                    tendencia = "decreased"
                else:
                    tendencia = "no changes"

            if fuente in fuentes:
                fuente_actual = fuentes[fuente]

            d = {
                "datetime" : datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                "currency": moneda,
                "data": {
                    "update_price": precio_actual,
                    "update_date": fecha_actual,
                    "update_time": hora_actual,
                    "source": fuente_actual,
                    "previous_price": precio_anterior,
                    "previous_date": fecha_anterior,
                    "previous_time": hora_anterior,
                    "difference": diferencia,
                    "trend": tendencia
                }
            }
            
            #logger.info(f"Datos EUR leídos: {d}")
            return d
        else:
            logger.warning(f"No se encontraron datos EUR para fuente={fuente}, fecha={fecha}")
            return {"message": f"No EUR data found for source={fuente}, date={fecha}"}
    except psycopg2.Error as e:
        logger.error(f"Error en la consulta de EUR: {e}")
        return {"error": str(e)}
    finally:
        if cursor:
            cursor.close()
        if conexion:
            pool.putconn(conexion)

def buscar_fecha(conexion, fecha, moneda, fuente: str | None = None):
    cursor = conexion.cursor()
    if not fuente:
        fuente = "bcv"
    try:
        sql = "SELECT precio, fecha, hora FROM detalle_precios WHERE fecha = %s AND moneda = %s AND fuente = %s"
        cursor.execute(sql, (fecha, moneda, fuente))
        rs = list(cursor.fetchone())

        rs[0] = str(rs[0])
        rs[1] = str(rs[1])
        rs[2] = str(rs[2])

        fuentes = {"bcv": "bcv", "c_d": "criptodolar", "i_c": "italcambio"}

        if fuente in fuentes:
            fuente = fuentes[fuente]

        logger.info(f"Datos encontrados para fecha {fecha}, moneda {moneda}: precio={rs[0]}, fecha={rs[1]}, hora={rs[2]}")

        d = {"price": rs[0],"date": rs[1], "time": rs[2], "source": fuente}
        return d
    except Exception as e:
        logger.warning(f"No se encontraron datos para fecha {fecha}, moneda {moneda}: {e}")
        return {"message": f"No data found for date {fecha}, currency {moneda}"}
    finally:
        if cursor:
            cursor.close()
        if conexion:
            pool.putconn(conexion)

def bancos(datos, valores: list):
    claves = {1: "Banesco",
              2: "BBVA Provincial",
              3: "Banco Mercantil",
              4: "Banco Plaza",
              5: "Banco Exterior",
              6: "Otras Instituciones",
              7: "Banco de Venezuela",
              8: "Banco Nacional de Crédito BNC",
              9: "Banco Activo",
              10: "Bancamiga",
              11: "BanCaribe",
              12: "Banplus",
              13: "R4",
              14: "N58 Banco Digital"}
    
    valor_a_clave = {v: k for k, v in claves.items()}
    conexion = None
    cursor = None

    try:
        # Get connection from pool
        conexion = pool.getconn()
        cursor = conexion.cursor()
        
        # Prepare the data
        filas_a_insertar = []
        for fila in datos:
            try:
                banco_nombre = fila[1]
                banco_id = valor_a_clave.get(banco_nombre)
                if not banco_id:
                    logger.warning(f"Banco no encontrado: {banco_nombre}")
                    continue
                    
                compra = fila[2] if fila[2] != '' else '00.00'
                venta = fila[3] if fila[3] != '' else '00.00'
                
                # Convert to float safely
                try:
                    compra = float(compra.replace(",", "."))
                    venta = float(venta.replace(",", "."))
                    filas_a_insertar.append((fila[0], banco_id, compra, venta))
                except (ValueError, AttributeError) as e:
                    logger.error(f"Error convirtiendo valores numéricos: {e}")
                    continue
                    
            except IndexError as e:
                logger.error(f"Error en el formato de los datos: {fila} - {e}")
                continue

        # Insert all rows in a single transaction
        if filas_a_insertar:
            sql = """
                INSERT INTO tasa_informativa (fecha, banco, compra, venta) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (banco, fecha) 
                DO UPDATE SET 
                    compra = EXCLUDED.compra,
                    venta = EXCLUDED.venta
            """
            cursor.executemany(sql, filas_a_insertar)
            conexion.commit()
            logger.info(f"Insertadas/actualizadas {len(filas_a_insertar)} filas en tasa_informativa")
            return {"message": f"Insertadas/actualizadas {len(filas_a_insertar)} filas"}
        else:
            logger.warning("No se encontraron filas válidas para insertar")
            return {"message": "No se encontraron filas válidas para insertar"}
            
    except Exception as e:
        if conexion:
            conexion.rollback()
        logger.error(f"Error general al insertar bancos: {e}")
        return {"error": str(e)}
        
    finally:
        if cursor:
            cursor.close()
        if conexion:
            pool.putconn(conexion)

def ver_tasa(conexion, fecha: str = None, banco: str = None):
    cursor = conexion.cursor()
    try:
        sql = """
            SELECT ti.fecha, b.nombre, ti.compra, ti.venta
            FROM tasa_informativa ti
            INNER JOIN bancos b ON ti.banco = b.id
            WHERE ti.fecha = (
                SELECT MAX(ti2.fecha)
                FROM tasa_informativa ti2
                WHERE ti2.banco = ti.banco
            )
        """
        params = []
        filtros = []

        if banco is not None and banco != "":
            filtros.append("b.nombre = %s")
            params.append(banco)
        if fecha is not None and fecha != "":
            filtros.append("ti.fecha = %s")
            params.append(fecha)
        
        if filtros:
            sql += " AND " + " AND ".join(filtros)
        
        sql += " GROUP BY ti.banco ORDER BY b.nombre ASC"

        cursor.execute(sql, params)
        rs = list(cursor.fetchall())

        if not rs:
            logger.warning("No se encontraron datos de tasa informativa")
            return {"success": False,
                    "error": {
                        "status_code": "404",
                        "message": "Data not found",
                        "details": f"Didn't find data for date {fecha} for {banco}"
                    }}

        result = []
        for row in rs:
            row_dict = {
                "date": str(row[0]),
                "bank": row[1],
                "buy_price": str(row[2]),
                "sell_price": str(row[3])
            }
            result.append(row_dict)

        logger.info("Tasa informativa consultada exitosamente")
        return {"tasa_informativa": result}
    except Exception as e:
        logger.error(f"Error al consultar tasa informativa: {e}")
        return {"tasa_informativa": None}
    finally:
        if cursor:
            cursor.close()
        if conexion:
            pool.putconn(conexion)

if __name__ == "__main__":
    logger.info("Script de base de datos iniciado")
    # Example usage
    conn = get_db_connection()
    try:
        crear_tablas(conn)
        print("Database setup completed successfully")
    except Exception as e:
        print(f"Error setting up database: {e}")
    finally:
        if conn:
            pool.putconn(conn)
