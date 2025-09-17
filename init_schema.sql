-- PostgreSQL database schema for FastAPI application

-- Create the database (run this in psql or your PostgreSQL client)
-- CREATE DATABASE base_api
--     WITH 
--     ENCODING = 'UTF8'
--     LC_COLLATE = 'en_US.UTF-8'
--     LC_CTYPE = 'en_US.UTF-8'
--     TEMPLATE = template0;

-- \c base_api

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: bancos
CREATE TABLE IF NOT EXISTS bancos (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL,
  CONSTRAINT uq_bancos_nombre UNIQUE (nombre)
);

-- Insert initial data into bancos
INSERT INTO bancos (nombre) VALUES 
  ('Banesco'),
  ('BBVA Provincial'),
  ('Banco Mercantil'),
  ('Banco Plaza'),
  ('Banco Exterior'),
  ('Otras Instituciones'),
  ('Banco de Venezuela'),
  ('Banco Nacional de Crédito BNC'),
  ('Banco Activo'),
  ('Bancamiga'),
  ('BanCaribe'),
  ('Banplus'),
  ('R4'),
  ('BCV')
ON CONFLICT (nombre) DO NOTHING;

-- View: detalle_precios
CREATE OR REPLACE VIEW detalle_precios AS 
SELECT 
    p.precio,
    p.fecha,
    p.hora,
    f.nombre AS fuente,
    m.nombre AS moneda
FROM precios p
INNER JOIN fuentes f ON p.fuente = f.id
INNER JOIN monedas m ON p.moneda = m.id;

-- Table: fuentes
CREATE TABLE IF NOT EXISTS fuentes (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(255) NOT NULL,
  CONSTRAINT uq_fuentes_nombre UNIQUE (nombre)
);

-- Insert initial data into fuentes
INSERT INTO fuentes (nombre) VALUES 
  ('bcv'),
  ('c_d'),
  ('i_c')
ON CONFLICT (nombre) DO NOTHING;

-- Table: monedas
CREATE TABLE IF NOT EXISTS monedas (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(255) NOT NULL,
  CONSTRAINT uq_monedas_nombre UNIQUE (nombre)
);

-- Insert initial data into monedas
INSERT INTO monedas (nombre) VALUES 
  ('USD'),
  ('EUR'),
  ('TRY'),
  ('RUB'),
  ('CNY')
ON CONFLICT (nombre) DO NOTHING;

-- Table: precios
CREATE TABLE IF NOT EXISTS precios (
  id SERIAL PRIMARY KEY,
  fuente INTEGER NOT NULL,
  moneda INTEGER NOT NULL,
  precio DECIMAL(10,2) NOT NULL,
  fecha DATE NOT NULL,
  hora TIME NOT NULL,
  CONSTRAINT fk_precios_fuente FOREIGN KEY (fuente) REFERENCES fuentes(id) ON DELETE CASCADE,
  CONSTRAINT fk_precios_moneda FOREIGN KEY (moneda) REFERENCES monedas(id) ON DELETE CASCADE,
  CONSTRAINT uq_precios UNIQUE (fuente, moneda, fecha, hora)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_precios_fuente ON precios(fuente);
CREATE INDEX IF NOT EXISTS idx_precios_moneda ON precios(moneda);
CREATE INDEX IF NOT EXISTS idx_precios_fecha ON precios(fecha);

-- Table: tasa_informativa
CREATE TABLE IF NOT EXISTS tasa_informativa (
  id SERIAL PRIMARY KEY,
  fecha DATE NOT NULL,
  banco INTEGER NOT NULL,
  compra DECIMAL(10,4) DEFAULT NULL,
  venta DECIMAL(10,4) DEFAULT NULL,
  CONSTRAINT fk_tasa_informativa_banco FOREIGN KEY (banco) REFERENCES bancos(id) ON DELETE CASCADE,
  CONSTRAINT uq_tasa_informativa_banco_fecha UNIQUE (banco, fecha)
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_tasa_informativa_banco ON tasa_informativa(banco);
CREATE INDEX IF NOT EXISTS idx_tasa_informativa_fecha ON tasa_informativa(fecha);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add created_at and updated_at columns to relevant tables
ALTER TABLE precios 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

ALTER TABLE tasa_informativa
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create triggers to update the updated_at column
CREATE TRIGGER update_precios_modtime
BEFORE UPDATE ON precios
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_tasa_informativa_modtime
BEFORE UPDATE ON tasa_informativa
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Create a function to get the latest exchange rate
CREATE OR REPLACE FUNCTION get_latest_rate(p_currency VARCHAR)
RETURNS TABLE (
    precio DECIMAL(10,2),
    fecha DATE,
    hora TIME,
    fuente VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.precio, p.fecha, p.hora, f.nombre as fuente
    FROM precios p
    JOIN fuentes f ON p.fuente = f.id
    JOIN monedas m ON p.moneda = m.id
    WHERE m.nombre = p_currency
    ORDER BY p.fecha DESC, p.hora DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;
