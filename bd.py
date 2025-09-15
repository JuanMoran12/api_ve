import sqlite3
import mariadb
import time
from datetime import datetime, timedelta
import asyncio
import logging
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    pool = mariadb.ConnectionPool(
        pool_name="api_pool",
        pool_size=10,
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    logger.info("Pool de conexiones de MariaDB creado exitosamente.")
except mariadb.Error as e:
    logger.critical(f"Error crítico al crear el pool de conexiones: {e}")
    raise

def get_db_connection():
    connection = None
    try:
        connection = pool.get_connection()
        yield connection
    finally:
        if connection:
            connection.close()

def crear_tablas(connection: mariadb.Connection):
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monedas (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(30) NOT NULL,
                UNIQUE KEY uq_monedas_nombre (nombre)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fuentes (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL,
                UNIQUE KEY uq_fuentes_nombre (nombre)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bancos (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(80) NOT NULL,
                UNIQUE KEY uq_bancos_nombre (nombre)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS precios (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                fuente INT NOT NULL,
                moneda INT NOT NULL,
                precio DECIMAL(10,2) NOT NULL,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                CONSTRAINT fk_precios_moneda FOREIGN KEY (moneda) REFERENCES monedas(id),
                CONSTRAINT fk_precios_fuente FOREIGN KEY (fuente) REFERENCES fuentes(id),
                UNIQUE KEY uq_precios (fuente, moneda, fecha, hora),
                KEY idx_precios_moneda (moneda),
                KEY idx_precios_fuente (fuente)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasa_informativa (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                fecha DATE NOT NULL,
                banco INT NOT NULL,
                compra DECIMAL(10,2) NOT NULL,
                venta  DECIMAL(10,2) NOT NULL,
                CONSTRAINT fk_tasa_banco FOREIGN KEY (banco) REFERENCES bancos(id),
                UNIQUE KEY uq_tasa (banco, fecha)
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
            "INSERT IGNORE INTO monedas (nombre) VALUES (?)",
            [("USD",), ("EUR",), ("TRY",), ("RUB",), ("CNY",)]
        )

        cursor.executemany(
            "INSERT IGNORE INTO fuentes (nombre) VALUES (?)",
            [("bcv",), ("c_d",), ("i_c",), ("e_m",)]
        )

        cursor.executemany(
            "INSERT IGNORE INTO bancos (nombre) VALUES (?)",
            [("Banesco",),("BBVA Provincial",),("Banco Mercantil",),("Banco Plaza",),
            ("Banco Exterior",),("Otras Instituciones",),("Banco de Venezuela",),
            ("Banco Nacional de Crédito BNC",),("Banco Activo",),("Bancamiga",),
            ("BanCaribe",),("Banplus",),("R4",)]
        )

        #connection.commit()
        logger.info("Tablas, vista y datos base creados/insertados correctamente")

    except mariadb.Error as e:
        logger.error(f"Error en la creación de tablas: {e}")

    finally:
        cursor.close()
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
        sql = "SELECT precio, fecha, hora FROM detalle_precios WHERE fecha = ?"
        params = [fecha]

        if moneda:
            sql += " AND moneda = ?"
            params.append(moneda)
        if fuente:
            sql += " AND fuente = ?"
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
        
    except mariadb.Error as e:
        logger.error(f"Error al consultar el precio para la fecha especificada: {e}")
        return {"error": f"Error en consulta: {str(e)}"}
    finally:
        cursor.close()
        connection.close()
        
def leer_usd(connection: mariadb.Connection, fuente: str | None = None, fecha: str | None = None):
    cursor = connection.cursor() 

    if not fuente:
        fuente = "bcv"
        #logger.info("Fuente no especificada, se usará 'bcv' por defecto.")

    if not fecha:
        fecha = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        sql = "SELECT precio, fecha, hora, fuente FROM detalle_precios WHERE moneda = ? and fuente = ?"
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

            print("Previous price data:" , precio_viejo)
            
            if precio_viejo and isinstance(precio_viejo, dict):
                try:
                    precio_anterior = float(precio_viejo.get("precio")) if precio_viejo.get("precio") is not None else None
                    fecha_anterior = str(precio_viejo.get("fecha")) if precio_viejo.get("fecha") is not None else None
                    hora_anterior = str(precio_viejo.get("hora")) if precio_viejo.get("hora") is not None else None
                    
                    if precio_anterior is None or fecha_anterior is None or hora_anterior is None:
                        logger.warning(f"Incomplete previous price data: {precio_viejo}")
                        # Continue with None values but don't calculate difference/trend
                        diferencia = None
                        tendencia = "no previous data"
                    if precio_anterior is not None:
                        diferencia = round(precio_actual - precio_anterior, 2)
                        if diferencia > 0:
                            tendencia = "increased"
                        elif diferencia < 0:
                            tendencia = "decreased"
                        else:
                            tendencia = "no changes"
                    else:
                        diferencia = None
                        tendencia = "no previous data"
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing previous price data: {e}")
                    diferencia = None
                    tendencia = "error in previous data"
            else:
                logger.warning("No previous price data available")
                diferencia = None
                tendencia = "no previous data"

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
            
    except mariadb.Error as e:
        logger.error(f"Error en la consulta de USD: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        connection.close()

def precio_usd(fuente, moneda, valor, fecha, hora):
    conexion = None
    cursor = None

    try:
        conexion: mariadb.Connection = pool.get_connection()
        cursor = conexion.cursor()

        sql = "insert into precios(fuente, moneda, precio, fecha, hora) values(?,?,?,?,?)"
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

def leer_eur(conexion: mariadb.Connection, moneda, fuente: str | None = None, fecha: str | None = None):
    cursor = conexion.cursor() 

    if not fuente:
        fuente = "bcv"
        logger.info("Fuente no especificada, se usará 'bcv' por defecto.")

    if not fecha:
        fecha = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        sql = "SELECT precio, fecha, hora, fuente FROM detalle_precios WHERE moneda = ? and fuente = ?"
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
            
            print("Previous price data:", precio_viejo)
            
            if precio_viejo and isinstance(precio_viejo, dict):
                try:
                    precio_anterior = float(precio_viejo.get("precio")) if precio_viejo.get("precio") is not None else None
                    fecha_anterior = str(precio_viejo.get("fecha")) if precio_viejo.get("fecha") is not None else None
                    hora_anterior = str(precio_viejo.get("hora")) if precio_viejo.get("hora") is not None else None
                    
                    if precio_anterior is None or fecha_anterior is None or hora_anterior is None:
                        logger.warning(f"Incomplete previous price data: {precio_viejo}")
                        diferencia = None
                        tendencia = "no previous data"
                    
                    if precio_anterior is not None:
                        diferencia = round(precio_actual - precio_anterior, 2)
                        if diferencia > 0:
                            tendencia = "increased"
                        elif diferencia < 0:
                            tendencia = "decreased"
                        else:
                            tendencia = "no changes"
                    else:
                        diferencia = None
                        tendencia = "no previous data"
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing previous price data: {e}")
                    diferencia = None
                    tendencia = "error in previous data"
            else:
                logger.warning("No previous price data available")
                diferencia = None
                tendencia = "no previous data"

            if fuente in fuentes:
                fuente_actual = fuentes[fuente]

            d = {
                "datetime": datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
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
            
            return d
        else:
            logger.warning(f"No se encontraron datos EUR para fuente={fuente}, fecha={fecha}")
            return {"message": f"No EUR data found for source={fuente}, date={fecha}"}
    except mariadb.Error as e:
        logger.error(f"Error en la consulta de EUR: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        conexion.close()

def buscar_fecha(conexion: mariadb.Connection ,fecha, moneda, fuente: str | None = None):
    cursor = conexion.cursor()
    if not fuente:
        fuente = "bcv"
    try:
        sql = "select precio, fecha, hora from detalle_precios where fecha = ? and moneda = ? and fuente = ?"
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
        cursor.close()
        conexion.close()

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
              13: "R4"}
    
    valor_a_clave = {v: k for k, v in claves.items()}

    filas_modificadas = []
    for fila in datos:
        nueva_fila = []
        for elemento in fila:
            if elemento in valor_a_clave:
                nueva_fila.append(valor_a_clave[elemento])  
            else:
                nueva_fila.append(elemento)
        filas_modificadas.append(list(nueva_fila))

    #print("Filas modificadas:", filas_modificadas)

    try:
        conexion = pool.get_connection()
        cursor = conexion.cursor()
        sql = "INSERT INTO tasa_informativa (fecha, banco, compra, venta) VALUES (?, ?, ?, ?)"
        for i in filas_modificadas:
            if i[2] == '':
                i[2] = '00,00'
            compra = i[2]
            compra = compra.replace(",", ".")
            venta = i[3]
            venta = venta.replace(",", ".")
            try:
                fila = (i[0], i[1], float(compra), float(venta))
                print("Insertando fila:", fila)
                cursor.execute(sql, fila)
            except Exception as e:
                logger.error(f"Error al insertar fila {i}: {e}")
        conexion.commit()
        logger.info(f"Insertadas filas en bancos_precios")
    except Exception as e:
        logger.error(f"Error general al insertar bancos: {e}")
        return {"error": str(e)}
    finally:
        cursor.close()
        conexion.close()

def ver_tasa(conexion: mariadb.Connection, fecha: str = None, banco: str = None):
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
            filtros.append("b.nombre = ?")
            params.append(banco)
        if fecha is not None and fecha != "":
            filtros.append("ti.fecha = ?")
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
        cursor.close()
        conexion.close()

if __name__ == "__main__":
    logger.info("Script de base de datos iniciado")
    #print(precio_ayer(moneda="usd", fuente="i_c"))