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
        // Cargar facultades
        const facultiesResponse = await fetch(`/get_faculties_by_institution/${institutionId}/`);
        if (!facultiesResponse.ok) throw new Error('Error cargando facultades');
        const faculties = await facultiesResponse.json();
        
        facultySelect.innerHTML = '<option value="">---------</option>';
        faculties.faculties.forEach(faculty => {
            facultySelect.add(new Option(faculty.name, faculty.id));
        });

    } catch (error) {
        console.error('Error:', error);
        facultySelect.innerHTML = '<option value="">Error cargando facultades</option>';
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



// =============================================
// SECCIÓN 7: CARGA DE LEARNING OUTCOMES (CHECKLIST)
// =============================================
function setupLearningOutcomesChecklist() {
    const subjectSelect = document.getElementById('id_subject');
    const learningOutcomesContainer = document.getElementById('learning_outcomes_container');
    const hiddenInput = document.getElementById('id_learning_outcomes');

    if (subjectSelect && learningOutcomesContainer) {
        subjectSelect.addEventListener('change', function() {
            const subjectId = this.value;
            
            if (subjectId) {
                // Mostrar indicador de carga
                learningOutcomesContainer.innerHTML = `
                    <div class="text-center py-3">
                        <i class="fas fa-spinner fa-spin"></i> Cargando resultados...
                    </div>`;

                fetch(`/get-learning-outcomes/?subject_id=${subjectId}`)
                    .then(response => {
                        if (!response.ok) throw new Error('Error en la respuesta del servidor');
                        return response.json();
                    })
                    .then(data => {
                        learningOutcomesContainer.innerHTML = '';
                        hiddenInput.value = '';
                        
                        if (data && data.length > 0) {
                            const checklist = document.createElement('div');
                            checklist.className = 'learning-outcomes-checklist';
                            
                            data.forEach(outcome => {
                                const checkboxContainer = document.createElement('div');
                                checkboxContainer.className = 'form-check mb-2';
                                
                                const checkbox = document.createElement('input');
                                checkbox.type = 'checkbox';
                                checkbox.className = 'form-check-input outcome-checkbox';
                                checkbox.name = 'learning_outcomes';
                                checkbox.value = outcome.id || outcome.code;
                                checkbox.id = `outcome-${outcome.id || outcome.code}`;
                                
                                checkbox.addEventListener('change', function() {
                                    updateSelectedOutcomes();
                                });
                                
                                const label = document.createElement('label');
                                label.className = 'form-check-label';
                                label.htmlFor = `outcome-${outcome.id || outcome.code}`;
                                
                                // Mostrar código y descripción si están disponibles
                                const description = outcome.code ? 
                                    `<strong>${outcome.code}:</strong> ${outcome.description}` : 
                                    outcome.description;
                                
                                label.innerHTML = description;
                                
                                checkboxContainer.appendChild(checkbox);
                                checkboxContainer.appendChild(label);
                                checklist.appendChild(checkboxContainer);
                            });
                            
                            learningOutcomesContainer.appendChild(checklist);
                        } else {
                            learningOutcomesContainer.innerHTML = `
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle"></i> 
                                    No se encontraron resultados de aprendizaje definidos para esta materia.
                                </div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Error al cargar learning outcomes:', error);
                        learningOutcomesContainer.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="fas fa-exclamation-triangle"></i> 
                                Error al cargar los resultados: ${error.message}
                            </div>`;
                    });
            } else {
                learningOutcomesContainer.innerHTML = `
                    <p class="text-muted">
                        <i class="fas fa-info-circle"></i> 
                        Seleccione una materia para ver los resultados de aprendizaje
                    </p>`;
                hiddenInput.value = '';
            }
        });

        function updateSelectedOutcomes() {
            const selected = Array.from(document.querySelectorAll('.outcome-checkbox:checked'))
                                .map(checkbox => checkbox.value);
            hiddenInput.value = selected.join(',');
        }

        // Disparar evento change si ya hay una materia seleccionada
        if (subjectSelect.value) {
            subjectSelect.dispatchEvent(new Event('change'));
        }
    }
}

function previewExamTemplate() {
    const form = document.getElementById('examTemplateForm');
    const previewContainer = document.getElementById('previewContainer');
    const previewContent = document.getElementById('previewContent');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Validación básica
    if (!form.elements['institution'].value || 
        !form.elements['faculty'].value || 
        !form.elements['career'].value || 
        !form.elements['subject'].value) {
        alert('Complete los campos requeridos');
        return;
    }

    // Obtener outcomes seleccionados
    const selectedOutcomes = Array.from(
        document.querySelectorAll('.outcome-checkbox:checked')
    ).map(checkbox => checkbox.value).join(',');

    // Configurar FormData
    const formData = new FormData(form);
    formData.set('learning_outcomes', selectedOutcomes);

    // Mostrar loading
    const btn = document.querySelector('button[onclick="previewExamTemplate()"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando...';
    btn.disabled = true;

    // Limpiar preview anterior
    previewContent.innerHTML = '';
    previewContainer.style.display = 'none';

    fetch('/exam-templates/preview/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Error al generar preview');
        return response.text();
    })
    .then(html => {
        previewContent.innerHTML = html;
        previewContainer.style.display = 'block';
        previewContainer.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(error => {
        console.error('Error:', error);
        previewContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> 
                Error al generar previsualización: ${error.message}
            </div>`;
        previewContainer.style.display = 'block';
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// Inicialización cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Verificación de que la función existe antes de llamarla
    if (typeof setupLearningOutcomesChecklist === 'function') {
        setupLearningOutcomesChecklist();
    } else {
        console.error('Error crítico: setupLearningOutcomesChecklist no está definida');
    }
});

// =============================================
// SECCIÓN 8: GUARDADO DE PLANTILLA
// =============================================
function setupSaveTemplate() {
    const saveBtn = document.getElementById('save-template-btn');
    if (!saveBtn) return;

    // Función de notificación mejorada
    const showNotification = (message, type = 'success') => {
        const container = document.getElementById('alerts-container') || document.body;
        container.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    };

    saveBtn.addEventListener('click', async function() {
        const form = document.getElementById('examTemplateForm');
        const formData = new FormData(form);

        // Agregar todos los campos posibles (sin validación)
        const optionalFields = {
            'exam_mode': document.getElementById('id_exam_mode')?.value || '',
            'resolution_time': document.getElementById('id_resolution_time')?.value || '',
            'learning_outcomes': Array.from(document.querySelectorAll('.outcome-checkbox:checked'))
                                .map(cb => cb.value).join(',')
        };

        // Agregar campos opcionales al FormData
        Object.entries(optionalFields).forEach(([key, value]) => {
            formData.append(key, value);
        });

        // Estado de carga
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        saveBtn.disabled = true;

        try {
            const response = await fetch('/exam-templates/save/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error al guardar la plantilla');
            }

            showNotification('Plantilla guardada correctamente');
            
        } catch (error) {
            console.error('Error:', error);
            showNotification(error.message, 'danger');
        } finally {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    });
}


// Asegúrate de que esta línea esté al final del DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // ... (tu código existente) ...
    setupSaveTemplate();
});

