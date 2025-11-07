# Mejoras en Cuestionarios Orales - Modo de Visualización

## 📋 Cambios Implementados

### 1. ✅ Conservar Formato al Cambiar Pregunta

**Problema anterior:**
- Al cambiar una pregunta, la página recargaba y volvía siempre al formato "Lista"
- Se perdía la selección del usuario

**Solución implementada:**
- Uso de `localStorage` para guardar la preferencia del modo de visualización
- Al recargar la página (después de cambiar pregunta o asignar nombres), se restaura automáticamente el modo que tenías seleccionado

**Código agregado:**
```javascript
// Al cargar la página, restaurar el modo guardado
const savedViewMode = localStorage.getItem('oralExamViewMode');
if (savedViewMode) {
    viewMode = savedViewMode;
    // Marcar el radio button correcto
    if (savedViewMode === 'roundRobin') {
        document.getElementById('roundRobinMode').checked = true;
        document.getElementById('roundRobinControls').style.display = 'block';
    } else {
        document.getElementById('listMode').checked = true;
        document.getElementById('roundRobinControls').style.display = 'none';
    }
}

// Al cambiar el modo, guardarlo
listMode.addEventListener('change', function() {
    if (this.checked) {
        viewMode = 'list';
        localStorage.setItem('oralExamViewMode', 'list');  // Guardar
        // ...
    }
});

roundRobinMode.addEventListener('change', function() {
    if (this.checked) {
        viewMode = 'roundRobin';
        localStorage.setItem('oralExamViewMode', 'roundRobin');  // Guardar
        // ...
    }
});
```

### 2. ✅ Round Robin como Formato Por Defecto

**Cambios realizados:**

1. **HTML - Radio buttons reordenados:**
   - Round Robin ahora aparece primero y tiene `checked` por defecto
   - Lista ahora es la segunda opción

2. **JavaScript - Variable inicial:**
   ```javascript
   // Antes:
   let viewMode = 'list';
   
   // Ahora:
   let viewMode = 'roundRobin';  // Round Robin como default
   ```

3. **Controles iniciales:**
   ```javascript
   // Si no hay modo guardado, usar Round Robin por defecto
   document.getElementById('roundRobinControls').style.display = 'block';
   ```

## 🎯 Comportamiento Actual

### Al Cargar Cuestionario Oral:
- ✅ **Modo por defecto:** Round Robin (controles de navegación visibles)
- ✅ **Asignación de nombres:** Carga en Round Robin

### Al Cambiar Pregunta:
1. Usuario está en Round Robin
2. Click en "Cambiar" pregunta
3. Selecciona nueva pregunta
4. Confirma el cambio
5. Página recarga
6. **✅ Vuelve automáticamente a Round Robin**

### Al Asignar Nombres:
1. Usuario está en Round Robin  
2. Ingresa nombres y asigna
3. Página recarga
4. **✅ Vuelve automáticamente a Round Robin**

### Persistencia:
- La preferencia se guarda en `localStorage` del navegador
- **Persiste entre sesiones** (si cerrás y abrís el navegador)
- **Persiste entre diferentes exámenes orales**
- Para resetear: cambiar manualmente el modo o limpiar localStorage

## 📁 Archivos Modificados

- ✅ `material/templates/material/oral_exams/view.html`
  - Radio buttons reordenados (Round Robin primero)
  - JavaScript actualizado para localStorage
  - Default cambiado a 'roundRobin'

## 🧪 Casos de Prueba

### Caso 1: Primera Carga
- ✅ Modo: Round Robin
- ✅ Controles: Visible (Anterior/Siguiente)
- ✅ Vista: Muestra solo Grupo 1, Pregunta 1

### Caso 2: Cambiar a Lista y Recargar
1. Cambiar a "Lista"
2. Recargar página (F5)
3. ✅ Debe mantener "Lista"

### Caso 3: Cambiar Pregunta en Round Robin
1. Estar en Round Robin
2. Cambiar una pregunta
3. ✅ Después de recargar, vuelve a Round Robin

### Caso 4: Asignar Nombres en Round Robin
1. Estar en Round Robin
2. Asignar nombres aleatorios
3. ✅ Después de recargar, vuelve a Round Robin

### Caso 5: Cerrar y Reabrir Navegador
1. Seleccionar Round Robin (o Lista)
2. Cerrar navegador completamente
3. Reabrir y cargar el mismo examen
4. ✅ Mantiene la última selección

## 🔧 Limpieza de Preferencias

Si necesitás resetear la preferencia guardada:

**Opción 1: Desde consola del navegador (F12)**
```javascript
localStorage.removeItem('oralExamViewMode');
location.reload();
```

**Opción 2: Cambiar manualmente**
- Simplemente hacer clic en el otro modo y ya se guarda la nueva preferencia

## ✨ Ventajas

1. **Experiencia de usuario mejorada**: No pierde el contexto al cambiar preguntas
2. **Modo preferido**: Round Robin es más intuitivo para toma oral
3. **Persistencia inteligente**: Recuerda tu preferencia
4. **Sin configuración adicional**: Funciona automáticamente

---

**Estado:** ✅ Implementado y funcionando  
**Fecha:** 7 de noviembre de 2025
