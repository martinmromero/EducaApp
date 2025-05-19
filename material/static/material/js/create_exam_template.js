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
// SECCIÓN 6: FUNCIONES ADICIONALES (PREVIEW)
// =============================================
/**
 * Función para previsualizar la plantilla de examen
 * (Implementación existente se mantiene igual)
 */
function previewExamTemplate() {
    // ... código existente ...
}

// =============================================
// SECCIÓN 7: CARGA DE LEARNING OUTCOMES (CHECKLIST)
// =============================================
// Reemplaza la función setupLearningOutcomesChecklist con esta versión mejorada

function setupLearningOutcomesChecklist() {
    const subjectSelect = document.getElementById('id_subject');
    const container = document.getElementById('learning_outcomes_container');
    const originalSelect = document.querySelector('select[name="learning_outcomes"]');

    if (!subjectSelect || !container) {
        console.error('Elementos del DOM no encontrados');
        return;
    }

    subjectSelect.addEventListener('change', async function() {
        const subjectId = this.value;
        
        // Mostrar estado de carga
        container.innerHTML = `
            <div class="outcome-loading">
                <i class="fas fa-spinner fa-spin"></i> Cargando resultados...
            </div>
        `;

        if (!subjectId) {
            container.innerHTML = `
                <div class="outcome-empty">
                    <i class="fas fa-info-circle"></i> Seleccione una materia primero
                </div>
            `;
            return;
        }

        try {
            console.log(`Solicitando outcomes para subject_id: ${subjectId}`); // Debug
            const response = await fetch(`/get-learning-outcomes/?subject_id=${subjectId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const outcomes = await response.json();
            console.log('Respuesta del servidor:', outcomes); // Debug

            if (!outcomes || outcomes.length === 0) {
                container.innerHTML = `
                    <div class="outcome-empty">
                        <i class="fas fa-exclamation-circle"></i> No hay resultados definidos para esta materia
                    </div>
                `;
                return;
            }

            // Construir checklist
            let html = '<div class="outcome-checklist">';
            outcomes.forEach(outcome => {
                // Verificar si ya estaba seleccionado
                const isSelected = originalSelect 
                    ? Array.from(originalSelect.options).some(opt => opt.value == outcome.id)
                    : false;
                
                html += `
                <div class="outcome-item">
                    <input type="checkbox" 
                           id="outcome_${outcome.id}" 
                           value="${outcome.id}"
                           ${isSelected ? 'checked' : ''}>
                    <label for="outcome_${outcome.id}">
                        <span class="outcome-code">${outcome.code}</span>
                        <span class="outcome-desc">${outcome.description}</span>
                        <span class="outcome-level">(Nivel ${outcome.level})</span>
                    </label>
                </div>
                `;
            });
            html += '</div>';

            container.innerHTML = html;

            // Actualizar select original cuando cambian los checkboxes
            container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    updateOriginalSelect(this.value, this.checked, originalSelect);
                });
            });

        } catch (error) {
            console.error('Error loading outcomes:', error);
            container.innerHTML = `
                <div class="outcome-error">
                    <i class="fas fa-exclamation-triangle"></i> Error al cargar resultados
                    <div class="error-details">${error.message}</div>
                </div>
            `;
        }
    });

    function updateOriginalSelect(value, isChecked, selectElement) {
        if (!selectElement) return;
        
        const existingOption = Array.from(selectElement.options).find(opt => opt.value === value);
        
        if (isChecked && !existingOption) {
            const newOption = new Option(value, value, true, true);
            selectElement.add(newOption);
        } else if (!isChecked && existingOption) {
            existingOption.remove();
        }
    }

    // Disparar evento change si ya hay una materia seleccionada
    if (subjectSelect.value) {
        subjectSelect.dispatchEvent(new Event('change'));
    }
}


document.addEventListener('DOMContentLoaded', function() {
    // Auto-formato de códigos al escribir
    const outcomesField = document.getElementById('id_learning_outcomes');
    if (outcomesField) {
        outcomesField.addEventListener('blur', function() {
            // Validación básica en cliente
            const lines = this.value.split('\n');
            const formatted = lines.map((line, index) => {
                line = line.trim();
                if (line && !line.includes(':') && !line.startsWith('LO-')) {
                    return `LO-${index+1}: ${line} - Nivel 1`;
                }
                return line;
            }).join('\n');
            
            if (formatted !== this.value) {
                this.value = formatted;
            }
        });
    }
});