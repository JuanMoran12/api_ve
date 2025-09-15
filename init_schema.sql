-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Versión del servidor:         11.5.2-MariaDB - mariadb.org binary distribution
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.6.0.6765
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para base_api
CREATE DATABASE IF NOT EXISTS `base_api` /*!40100 DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci */;
USE `base_api`;

-- Volcando estructura para tabla base_api.bancos
CREATE TABLE IF NOT EXISTS `bancos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Volcando datos para la tabla base_api.bancos: ~14 rows (aproximadamente)
INSERT IGNORE INTO `bancos` (`id`, `nombre`) VALUES
	(1, 'Banesco'),
	(2, 'BBVA Provincial'),
	(3, 'Banco Mercantil'),
	(4, 'Banco Plaza'),
	(5, 'Banco Exterior'),
	(6, 'Otras Instituciones'),
	(7, 'Banco de Venezuela'),
	(8, 'Banco Nacional de Crédito BNC'),
	(9, 'Banco Activo'),
	(10, 'Bancamiga'),
	(11, 'BanCaribe'),
	(12, 'Banplus'),
	(13, 'R4'),
	(14, 'BCV');

-- Volcando estructura para vista base_api.detalle_precios
-- Creando tabla temporal para superar errores de dependencia de VIEW
CREATE TABLE `detalle_precios` (
	`precio` DECIMAL(10,2) NOT NULL,
	`fecha` DATE NOT NULL,
	`hora` TIME NOT NULL,
	`fuente` VARCHAR(255) NOT NULL COLLATE 'latin1_swedish_ci',
	`moneda` VARCHAR(255) NOT NULL COLLATE 'latin1_swedish_ci'
) ENGINE=MyISAM;

-- Volcando estructura para tabla base_api.fuentes
CREATE TABLE IF NOT EXISTS `fuentes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Volcando datos para la tabla base_api.fuentes: ~14 rows (aproximadamente)
INSERT IGNORE INTO `fuentes` (`id`, `nombre`) VALUES
	(1, 'bcv'),
	(2, 'c_d'),
	(3, 'i_c'),
	(4, 'P2P'),
	(5, 'e_m'),
	(6, 'bcv'),
	(7, 'c_d'),
	(8, 'i_c'),
	(9, 'bcv'),
	(10, 'c_d'),
	(11, 'i_c'),
	(12, 'bcv'),
	(13, 'c_d'),
	(14, 'i_c');

-- Volcando estructura para tabla base_api.monedas
CREATE TABLE IF NOT EXISTS `monedas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Volcando datos para la tabla base_api.monedas: ~11 rows (aproximadamente)
INSERT IGNORE INTO `monedas` (`id`, `nombre`) VALUES
	(1, 'USD'),
	(2, 'EUR'),
	(3, 'TRY'),
	(4, 'RUB'),
	(5, 'CNY'),
	(6, 'USD'),
	(7, 'EUR'),
	(9, 'USD'),
	(10, 'EUR'),
	(12, 'USD'),
	(13, 'EUR');

-- Volcando estructura para tabla base_api.precios
CREATE TABLE IF NOT EXISTS `precios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fuente` int(11) NOT NULL,
  `moneda` int(11) NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fuente` (`fuente`),
  KEY `moneda` (`moneda`),
  CONSTRAINT `precios_ibfk_1` FOREIGN KEY (`fuente`) REFERENCES `fuentes` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `precios_ibfk_2` FOREIGN KEY (`moneda`) REFERENCES `monedas` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=318 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Volcando estructura para tabla base_api.tasa_informativa
CREATE TABLE IF NOT EXISTS `tasa_informativa` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fecha` date NOT NULL,
  `banco` int(11) NOT NULL,
  `compra` decimal(10,4) DEFAULT NULL,
  `venta` decimal(10,4) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `banco` (`banco`),
  CONSTRAINT `tasa_informativa_ibfk_1` FOREIGN KEY (`banco`) REFERENCES `bancos` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=239 DEFAULT CHARSET=latin1 COLLATE=latin1_swedish_ci;

-- Eliminando tabla temporal y crear estructura final de VIEW
DROP TABLE IF EXISTS `detalle_precios`;
CREATE ALGORITHM=UNDEFINED SQL SECURITY DEFINER VIEW `detalle_precios` AS SELECT 
                p.precio,
                p.fecha,
                p.hora,
                f.nombre AS fuente,
                m.nombre AS moneda
            FROM precios p
            INNER JOIN fuentes  f ON p.fuente = f.id
            INNER JOIN monedas  m ON p.moneda = m.id ;

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
