// Funcionalidad principal
document.addEventListener('DOMContentLoaded', function() {
    initializeFormHandlers();
    setupDynamicSelects();
});

function initializeFormHandlers() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Manejador para botones "Nuevo/Guardar"
    document.querySelectorAll('.dynamic-add-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            await handleDynamicAddButton(this, csrfToken);
        });
    });

    // Si necesitas otros handlers del formulario, agregarlos aquí
}

function setupDynamicSelects() {
    const institutionSelect = document.getElementById('id_institution');
    
    // Cargar inicialmente si hay institución seleccionada
    if (institutionSelect && institutionSelect.value) {
        loadDependents(institutionSelect.value);
    }

    // Cambio de institución
    institutionSelect?.addEventListener('change', function() {
        loadDependents(this.value);
    });
}

// Funciones auxiliares (las mismas que ya tenías, pero modularizadas)
async function loadDependents(institutionId) {
    // ... implementación existente ...
}

function showToast(message, type = 'success') {
    // ... implementación existente ...
}

async function handleDynamicAddButton(button, csrfToken) {
    // ... implementación existente del handler ...
}

// Mantén previewExamTemplate si se usa en otros lugares
function previewExamTemplate() {
    // ... implementación existente ...
}