-- =============================================
-- Script para crear una instancia LocalDB (ideal para desarrollo)
-- y la base de datos EducaAppDB con todas las tablas
-- =============================================

-- 1. Verificar/crear la instancia LocalDB (solo si usas SQL Server Express LocalDB)
PRINT 'Iniciando creación de entorno SQL Server...';
GO

-- Esto es para desarrollo local. Para producción necesitarías un servidor real.
-- Si ya tienes SQL Server instalado, omite esta parte y usa tu instancia existente.

-- 2. Crear la base de datos (con configuración optimizada para Django)
USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'EducaAppDB')
BEGIN
    CREATE DATABASE [EducaAppDB]
    ON PRIMARY 
    (
        NAME = N'EducaAppDB',
        FILENAME = N'C:\SQLData\EducaAppDB.mdf',  -- Ajusta la ruta según tu sistema
        SIZE = 100MB,
        MAXSIZE = UNLIMITED,
        FILEGROWTH = 20%
    )
    LOG ON 
    (
        NAME = N'EducaAppDB_log',
        FILENAME = N'C:\SQLData\EducaAppDB_log.ldf',
        SIZE = 50MB,
        MAXSIZE = 1GB,
        FILEGROWTH = 10%
    );
    
    PRINT 'Base de datos EducaAppDB creada exitosamente.';
END
ELSE
BEGIN
    PRINT 'La base de datos EducaAppDB ya existe.';
END
GO

-- 3. Configurar la base de datos para compatibilidad con Django
USE [EducaAppDB];
GO

-- Habilitar características necesarias
ALTER DATABASE [EducaAppDB] SET ALLOW_SNAPSHOT_ISOLATION ON;
ALTER DATABASE [EducaAppDB] SET READ_COMMITTED_SNAPSHOT ON;
GO

-- 4. Crear esquema principal (opcional pero recomendado)
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'educa')
BEGIN
    EXEC('CREATE SCHEMA [educa] AUTHORIZATION [dbo]');
    PRINT 'Esquema [educa] creado.';
END
GO

-- 5. Crear tablas (versión optimizada para el proyecto actual)
-- Institution
CREATE TABLE [educa].[Institution] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    address NVARCHAR(200),
    logo VARBINARY(MAX) NULL,
    created_at DATETIME2 DEFAULT SYSDATETIME(),
    updated_at DATETIME2 DEFAULT SYSDATETIME()
);
GO

-- Subject (Materias)
CREATE TABLE [educa].[Subject] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    code NVARCHAR(20),
    description NVARCHAR(500),
    created_at DATETIME2 DEFAULT SYSDATETIME()
);
GO

-- Content (antes Material)
CREATE TABLE [educa].[Content] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(200) NOT NULL,
    file_path NVARCHAR(500) NOT NULL,  -- Ruta relativa al sistema de archivos
    original_filename NVARCHAR(255) NOT NULL,
    file_size INT NOT NULL,
    file_type NVARCHAR(50) NOT NULL,
    upload_status NVARCHAR(20) DEFAULT 'Completo',
    uploaded_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    uploaded_by_id INT NOT NULL,  -- Se vinculará con Django
    subject_id INT NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES [educa].[Subject](id)
);
GO

-- Question
CREATE TABLE [educa].[Question] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    question_text NVARCHAR(MAX) NOT NULL,
    answer_text NVARCHAR(MAX) NOT NULL,
    topic NVARCHAR(100),
    subtopic NVARCHAR(100),
    chapter NVARCHAR(50),
    difficulty TINYINT DEFAULT 2,  -- 1: Fácil, 2: Medio, 3: Difícil
    is_approved BIT DEFAULT 0,
    content_id INT,
    subject_id INT NOT NULL,
    created_by_id INT NOT NULL,  -- Se vinculará con Django
    created_at DATETIME2 DEFAULT SYSDATETIME(),
    updated_at DATETIME2 DEFAULT SYSDATETIME(),
    FOREIGN KEY (content_id) REFERENCES [educa].[Content](id) ON DELETE SET NULL,
    FOREIGN KEY (subject_id) REFERENCES [educa].[Subject](id)
);
GO

-- ExamTemplate
CREATE TABLE [educa].[ExamTemplate] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(150) NOT NULL,
    institution_id INT NOT NULL,
    subject_id INT NOT NULL,
    instructions NVARCHAR(MAX),
    footer_text NVARCHAR(500),
    default_duration INT DEFAULT 90,  -- Minutos
    created_at DATETIME2 DEFAULT SYSDATETIME(),
    created_by_id INT NOT NULL,  -- Se vinculará con Django
    FOREIGN KEY (institution_id) REFERENCES [educa].[Institution](id),
    FOREIGN KEY (subject_id) REFERENCES [educa].[Subject](id)
);
GO

-- Exam
CREATE TABLE [educa].[Exam] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(200) NOT NULL,
    template_id INT,
    exam_date DATE,
    duration INT,  -- Minutos
    notes NVARCHAR(MAX),
    is_published BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT SYSDATETIME(),
    created_by_id INT NOT NULL,  -- Se vinculará con Django
    FOREIGN KEY (template_id) REFERENCES [educa].[ExamTemplate](id)
);
GO

-- ExamQuestion
CREATE TABLE [educa].[ExamQuestion] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    exam_id INT NOT NULL,
    question_id INT NOT NULL,
    question_order INT NOT NULL,
    points DECIMAL(5,2) DEFAULT 1.00,
    section NVARCHAR(100),
    FOREIGN KEY (exam_id) REFERENCES [educa].[Exam](id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES [educa].[Question](id),
    CONSTRAINT UQ_ExamQuestion_Order UNIQUE (exam_id, question_order)
);
GO

-- ProfessorInstitution
CREATE TABLE [educa].[ProfessorInstitution] (
    id INT IDENTITY(1,1) PRIMARY KEY,
    professor_id INT NOT NULL,  -- Se vinculará con Django
    institution_id INT NOT NULL,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (institution_id) REFERENCES [educa].[Institution](id) ON DELETE CASCADE
);
GO

-- 6. Crear índices para optimización
CREATE INDEX IX_Content_uploaded_by ON [educa].[Content](upload