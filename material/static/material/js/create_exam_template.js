/**
 * create_exam_template.js - Maneja la creación dinámica de elementos en el formulario de plantillas de examen
 * 
 * Funcionalidades principales:
 * - Carga dependiente de facultades/campus según institución seleccionada
 * - Creación dinámica de nuevos elementos (instituciones, facultades, campus, etc.)
 * - Notificaciones toast para feedback al usuario
 * 
 * Estructura:
 * 1. Configuración inicial y selección de elementos DOM
 * 2. Función para cargar dependientes (facultades/campus)
 * 3. Función para mostrar notificaciones toast
 * 4. Manejadores para botones dinámicos "Nuevo/Guardar"
 * 5. Event listeners iniciales
 */

document.addEventListener('DOMContentLoaded', function() {
    // =============================================
    // SECCIÓN 1: CONFIGURACIÓN INICIAL Y SELECTORES
    // =============================================
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const institutionSelect = document.getElementById('id_institution');
    const facultySelect = document.getElementById('id_faculty');
    const campusSelect = document.getElementById('id_campus');
    const previewContainer = document.getElementById('previewContainer');
    const previewContent = document.getElementById('previewContent');

    // =============================================
    // SECCIÓN 2: CARGA DE DEPENDIENTES (FACULTADES/CAMPUS)
    // =============================================
    /**
     * Carga facultades y campus basados en la institución seleccionada
     * @param {string} institutionId - ID de la institución seleccionada
     */
    async function loadDependents(institutionId) {
        if (!institutionId) {
            facultySelect.innerHTML = '<option value="">---------</option>';
            campusSelect.innerHTML = '<option value="">---------</option>';
            return;
        }

        try {
            // Mostrar estado de carga
            facultySelect.disabled = true;
            campusSelect.disabled = true;
            
            // Cargar facultades
            const facultiesResponse = await fetch(`/get_faculties_by_institution/${institutionId}/`);
            if (!facultiesResponse.ok) throw new Error('Error cargando facultades');
            const faculties = await facultiesResponse.json();
            
            facultySelect.innerHTML = '<option value="">---------</option>';
            faculties.faculties.forEach(faculty => {
                facultySelect.add(new Option(faculty.name, faculty.id));
            });

            // Cargar sedes
            const campusesResponse = await fetch(`/get_campuses_by_institution/${institutionId}/`);
            if (!campusesResponse.ok) throw new Error('Error cargando sedes');
            const campuses = await campusesResponse.json();
            
            campusSelect.innerHTML = '<option value="">---------</option>';
            campuses.campuses.forEach(campus => {
                campusSelect.add(new Option(campus.name, campus.id));
            });

        } catch (error) {
            console.error('Error:', error);
            facultySelect.innerHTML = '<option value="">---------</option>';
            campusSelect.innerHTML = '<option value="">---------</option>';
            showToast('Error al cargar dependencias', 'error');
        } finally {
            facultySelect.disabled = false;
            campusSelect.disabled = false;
        }
    }

    // =============================================
    // SECCIÓN 3: NOTIFICACIONES TOAST
    // =============================================
    /**
     * Muestra una notificación toast al usuario
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - Tipo de notificación ('success' o 'error')
     */
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }, 100);
    }

    // =============================================
    // SECCIÓN 4: MANEJADORES PARA BOTONES DINÁMICOS
    // =============================================
    /**
     * Configura los manejadores para los botones "Nuevo/Guardar" dinámicos
     * - Alterna entre modo "Nuevo" y "Guardar"
     * - Valida los datos antes de enviar
     * - Maneja la creación de nuevos elementos via API
     */
    document.querySelectorAll('.dynamic-add-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const target = this.dataset.target; // Tipo de elemento: institution, campus, faculty, career, subject
            const inputField = document.getElementById(`new_${target}`);
            const selectField = document.getElementById(this.dataset.field);
            const parentField = this.dataset.parent ? document.getElementById(this.dataset.parent) : null;
            const cancelBtn = this.nextElementSibling?.classList.contains('dynamic-cancel-btn') ? this.nextElementSibling : null;

            // Modo "Nuevo" - Mostrar campo de entrada
            if (inputField.style.display === 'none' || inputField.style.display === '') {
                inputField.style.display = 'block';
                this.innerHTML = '<i class="fas fa-save"></i> Guardar';
                this.classList.replace('btn-outline-secondary', 'btn-success');
                
                // Crear botón de cancelar si no existe
                if (!cancelBtn) {
                    const newCancelBtn = document.createElement('button');
                    newCancelBtn.className = 'btn btn-sm btn-danger dynamic-cancel-btn ml-2';
                    newCancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancelar';
                    newCancelBtn.onclick = () => {
                        inputField.value = '';
                        inputField.style.display = 'none';
                        this.innerHTML = '<i class="fas fa-plus"></i> Nuevo';
                        this.classList.replace('btn-success', 'btn-outline-secondary');
                        if (selectField) selectField.disabled = false;
                        newCancelBtn.remove();
                    };
                    this.parentNode.insertBefore(newCancelBtn, this.nextSibling);
                }

                if (selectField) selectField.disabled = true;
                inputField.focus();
                return;
            }

            // Modo "Guardar" - Validar y enviar datos
            const name = inputField.value.trim();
            if (!name) {
                showToast('Ingrese un nombre válido', 'error');
                return;
            }

            if (parentField && !parentField.value && target !== 'institution' && target !== 'career' && target !== 'subject') {
                showToast(`Seleccione ${parentField.labels[0].textContent} primero`, 'error');
                return;
            }

            try {
                const response = await fetch('/api/create-related-element/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        type: target,
                        name: name,
                        institution_id: parentField ? parentField.value : null
                    })
                });

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Error desconocido');
                }

                // Actualizar el select correspondiente
                if (selectField) {
                    const option = new Option(data.name, data.id);
                    selectField.add(option);
                    selectField.value = data.id;
                    selectField.disabled = false;
                }

                // Resetear campos
                inputField.value = '';
                inputField.style.display = 'none';
                this.innerHTML = '<i class="fas fa-plus"></i> Nuevo';
                this.classList.replace('btn-success', 'btn-outline-secondary');
                
                // Eliminar botón cancelar
                if (cancelBtn) cancelBtn.remove();
                
                // Mostrar feedback
                const elementNames = {
                    'institution': 'Institución',
                    'campus': 'Sede',
                    'faculty': 'Facultad',
                    'career': 'Carrera',
                    'subject': 'Materia'
                };
                showToast(`${elementNames[target]} creada con éxito`);

                // Recargar dependencias si es necesario
                if (target === 'institution' && institutionSelect.value) {
                    loadDependents(institutionSelect.value);
                }

            } catch (error) {
                console.error(`Error creando ${target}:`, error);
                showToast(error.message, 'error');
            }
        });
    });

    // =============================================
    // SECCIÓN 5: EVENT LISTENERS INICIALES
    // =============================================
    // Cargar dependientes si hay institución seleccionada al inicio
    if (institutionSelect && institutionSelect.value) {
        loadDependents(institutionSelect.value);
    }

    // Listener para cambios en la institución
    institutionSelect?.addEventListener('change', function() {
        loadDependents(this.value);
    });
});

// =============================================
// SECCIÓN 6: FUNCIONES DE PREVIEW MEJORADA
// =============================================
/**
 * Función para previsualizar la plantilla de examen en nueva ventana
 */
 // =============================================
    // SECCIÓN 6: FUNCIONES DE PREVIEW MEJORADA
    // =============================================
// create_exam_template.js
// REEMPLAZA LA FUNCIÓN COMPLETA POR ESTA VERSIÓN:
/* function setupPreviewButton() {
    const previewBtn = document.getElementById('previewBtn');
    if (!previewBtn) return;

    previewBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Validación rápida
        const examMode = document.getElementById('id_exam_mode').value;
        if (!examMode) {
            alert('Seleccione la modalidad del examen');
            return;
        }

        // Indicador de carga
        const originalText = previewBtn.innerHTML;
        previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
        previewBtn.disabled = true;

        // Preparar datos
        const form = document.getElementById('examTemplateForm');
        const formData = new FormData(form);

        // Enviar datos
        fetch('/exam-templates/preview/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => {
            previewBtn.innerHTML = originalText;
            previewBtn.disabled = false;
            
            if (!response.ok) throw new Error('Error del servidor');
            return response.text();
        })
        .then(html => {
            document.getElementById('previewContent').innerHTML = html;
            document.getElementById('previewContainer').style.display = 'block';
        })
        .catch(error => {
            console.error('Preview error:', error);
            alert('Error al generar previsualización');
        });
    });
}

// Agregar al final del DOMContentLoaded:
document.addEventListener('DOMContentLoaded', function() {
    // ... (todo tu código existente) ...
    setupPreviewButton();  // <-- Esta línea nueva
}); */

    // toda la funcion siguiente si se reemplazó OK con la de arriba function setupPreviewButton() , borrarla
function previewExamTemplate() {
    // 1. Validar campos requeridos
    const examMode = document.getElementById('id_exam_mode').value;
    if (!examMode) {
        alert('Por favor seleccione la modalidad del examen');
        return;
    }

    // 2. Configurar elementos UI
    const previewBtn = document.querySelector('button[onclick="previewExamTemplate()"]');
    const originalText = previewBtn.innerHTML;
    previewBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
    previewBtn.disabled = true;
    
    const previewContainer = document.getElementById('previewContainer');
    const previewContent = document.getElementById('previewContent');
    previewContainer.style.display = 'none';
    previewContent.innerHTML = '';

    // 3. Preparar datos del formulario
    const form = document.getElementById('examTemplateForm');
    const formData = new FormData(form);

    // 4. Enviar datos al servidor
    fetch('/exam-templates/preview/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
        }
        return response.text();
    })
    .then(html => {
        previewContent.innerHTML = html;
        previewContainer.style.display = 'block';
        previewContainer.scrollIntoView({ 
            behavior: 'smooth',
            block: 'nearest'
        });
    })
    .catch(error => {
        console.error('Error en preview:', error);
        previewContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Error al generar la previsualización
                <div class="error-details">${error.message}</div>
            </div>`;
        previewContainer.style.display = 'block';
    })
    .finally(() => {
        previewBtn.innerHTML = originalText;
        previewBtn.disabled = false;
    });
}

// =============================================
// SECCIÓN 7: CARGA DE LEARNING OUTCOMES (CHECKLIST)
// =============================================
// Reemplaza la función setupLearningOutcomesChecklist con esta versión mejorada

// Actualización de la función setupLearningOutcomesChecklist

function setupLearningOutcomesChecklist() {
    const subjectSelect = document.getElementById('id_subject');
    const container = document.getElementById('learning_outcomes_container');
    const hiddenInput = document.getElementById('id_learning_outcomes');
    
    // Función para actualizar los outcomes seleccionados
    function updateSelectedOutcomes() {
        const selected = [];
        document.querySelectorAll('.outcome-checkbox:checked').forEach(checkbox => {
            selected.push(checkbox.value);
        });
        hiddenInput.value = selected.join(',');
        console.log('Selected outcomes:', hiddenInput.value);
    }

    // Cargar outcomes cuando cambia la materia
    subjectSelect?.addEventListener('change', async function() {
        const subjectId = this.value;
        container.innerHTML = '<p>Cargando resultados...</p>';
        
        if (!subjectId) {
            container.innerHTML = '<p>Seleccione una materia primero</p>';
            return;
        }

        try {
            const response = await fetch(`/get-learning-outcomes/?subject_id=${subjectId}`);
            const outcomes = await response.json();
            
            if (!outcomes || outcomes.length === 0) {
                container.innerHTML = '<p>No hay resultados definidos para esta materia</p>';
                return;
            }

            let html = '';
            outcomes.forEach(outcome => {
                html += `
                <div>
                    <input type="checkbox" class="outcome-checkbox" 
                           id="outcome_${outcome.id}" value="${outcome.id}">
                    <label for="outcome_${outcome.id}">
                        ${outcome.code}: ${outcome.description}
                    </label>
                </div>
                `;
            });
            
            container.innerHTML = html;
            
            // Añadir listeners a los nuevos checkboxes
            container.querySelectorAll('.outcome-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', updateSelectedOutcomes);
            });

        } catch (error) {
            console.error('Error:', error);
            container.innerHTML = '<p>Error al cargar resultados</p>';
        }
    });

    // Actualizar outcomes antes de enviar el preview
    const previewBtn = document.querySelector('button[onclick="previewExamTemplate()"]');
    if (previewBtn) {
        previewBtn.addEventListener('click', function() {
            updateSelectedOutcomes();
        });
    }

    // Inicializar si hay materia seleccionada
    if (subjectSelect.value) {
        subjectSelect.dispatchEvent(new Event('change'));
    }
}

// Asegurarse de llamar a la función cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    setupLearningOutcomesChecklist();
});