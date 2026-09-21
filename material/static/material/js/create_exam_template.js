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
    // Todo el guardado real de esta pantalla pasa por el botón "Guardar
    // Plantilla" (type="button", fetch() propio, más abajo) — el <form>
    // nativo nunca debería sumitirse solo. Sin este guard, tipear en
    // cualquier campo de texto y apretar Enter (comportamiento estándar
    // del navegador en un form sin botón submit real) dispara un submit
    // nativo que SIEMPRE falla: institution_v2Form fuerza los querysets de
    // faculty/campus a .none() incondicionalmente (son requeridos vía
    // cascada AJAX, no por <select> plano), así que ese submit nunca puede
    // validar. En creación fallaba en silencio total (sin rama else en la
    // vista); acá se corta antes de que llegue a pasar.
    const examTemplateFormEl = document.getElementById('examTemplateForm');
    if (examTemplateFormEl) {
        examTemplateFormEl.addEventListener('submit', function(e) {
            e.preventDefault();
        });
    }

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
        if (campusSelect) campusSelect.innerHTML = '<option value="">---------</option>';
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
// Expuesto para que el script inline de modo edición (ver
// create_exam_template.html) pueda esperar a que termine ESTA MISMA carga
// en vez de arrancar una segunda en paralelo, y saber con certeza cuándo
// ya hay opciones de facultad para poder seleccionar la actual — antes se
// adivinaba con un setTimeout fijo (500ms) que no alcanzaba si el fetch
// tardaba más (típico en producción, no tanto en localhost), dejando
// "Facultad" en blanco pese a que la plantilla sí la tenía guardada.
window.EducaAppLoadTemplateDependents = loadDependents;

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
    // Cargar dependientes si hay institución seleccionada al inicio (modo
    // edición: la institución ya viene con valor desde el servidor). Se
    // guarda la promesa para que el script inline de modo edición pueda
    // esperar a ESTA carga en vez de arrancar una segunda en paralelo.
    if (institutionSelect && institutionSelect.value) {
        window.EducaAppTemplateDependentsReady = loadDependents(institutionSelect.value);
    }

    // Listener para cambios en la institución
    institutionSelect?.addEventListener('change', function() {
        loadDependents(this.value);
    });

    // =============================================
    // SECCIÓN 5b: CASCADA FACULTAD→CARRERA Y CARRERA→MATERIA
    // =============================================
    // Antes esta forma clásica no filtraba Carrera por Facultad ni
    // reordenaba Materia por Carrera (mostraba siempre el catálogo
    // completo) — el asistente (create_exam_template_wizard.js) sí lo
    // hacía. Mismo criterio acá para que las dos UI se comporten igual.
    // NO se dispara solo, únicamente al cambiar Facultad/Carrera a mano —
    // así no pisa la precarga en modo edición (que asigna .value sin
    // dispatchear 'change').
    const careerSelect = document.getElementById('id_career');
    const subjectSelect = document.getElementById('id_subject');
    let subjectsReorderedForCareer = null;

    if (facultySelect && careerSelect) {
        facultySelect.addEventListener('change', function () {
            const facultyId = this.value;
            if (!facultyId) return;
            fetch(`/get-careers-by-faculty/${facultyId}/`)
                .then(r => r.json())
                .then(data => {
                    const previousValue = careerSelect.value;
                    careerSelect.innerHTML = '<option value="">Seleccionar carrera</option>';
                    (data.careers || []).forEach(c => careerSelect.add(new Option(c.name, c.id)));
                    // Si la carrera que ya estaba elegida sigue siendo válida
                    // para la nueva facultad, se mantiene — si no, queda en
                    // blanco (mismo criterio que loadDependents con facultad).
                    if ([...careerSelect.options].some(o => o.value === previousValue)) {
                        careerSelect.value = previousValue;
                    }
                })
                .catch(() => { console.error('Error cargando carreras por facultad'); });
        });
    }

    if (careerSelect && subjectSelect) {
        careerSelect.addEventListener('change', function () {
            const careerId = this.value;
            if (!careerId || careerId === subjectsReorderedForCareer) return;
            const previousValue = subjectSelect.value;
            const allOptions = Array.from(subjectSelect.querySelectorAll('option[value]')).filter(o => o.value);

            fetch(`/get-subjects-by-career/${careerId}/`)
                .then(r => r.json())
                .then(data => {
                    const careerIds = (data.subjects || []).map(s => String(s.id));
                    const groupCareer = [], groupRest = [];
                    allOptions.forEach(opt => (careerIds.includes(opt.value) ? groupCareer : groupRest).push(opt));

                    subjectSelect.innerHTML = '';
                    const placeholder = new Option('---------', '');
                    subjectSelect.appendChild(placeholder);
                    function appendGroup(label, opts) {
                        if (!opts.length) return;
                        const group = document.createElement('optgroup');
                        group.label = label;
                        opts.forEach(o => group.appendChild(o));
                        subjectSelect.appendChild(group);
                    }
                    appendGroup('De esta carrera', groupCareer);
                    appendGroup('Todas las demás', groupRest);
                    subjectSelect.value = previousValue;
                    subjectsReorderedForCareer = careerId;
                })
                .catch(() => { console.error('Error reordenando materias por carrera'); });
        });
    }
});

// =============================================
// SECCIÓN 6: FUNCIONES DE PREVIEW
// =============================================

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

    // Los checkboxes de rúbrica no tienen atributo "name" (los arma
    // handleSave a mano al guardar, ver más abajo) — sin este mismo paso
    // acá, la vista previa nunca recibía ninguna rúbrica seleccionada y la
    // sección de Rúbricas quedaba ausente del todo, aunque sí quedaban
    // guardadas y visibles una vez guardada la plantilla.
    const selectedRubrics = Array.from(
        document.querySelectorAll('.rubric-checkbox:checked')
    ).map(checkbox => checkbox.value).join(',');

    // Configurar FormData
    const formData = new FormData(form);
    formData.set('learning_outcomes', selectedOutcomes);
    formData.set('rubrics', selectedRubrics);
    formData.set('csrfmiddlewaretoken', csrfToken);

    // La previsualización se abre en una PESTAÑA NUEVA de verdad (POST real
    // hacia una ventana con nombre único, abierta explícitamente con
    // window.open ANTES de armar el <form> -- no con fetch()+iframe, esa
    // versión anterior arreglaba zoom/dark-mode (documento aislado) pero
    // "Volver" ahí adentro navegaba el iframe a la pantalla completa de
    // /exam-templates/ apretada en una caja chica (reportado: "se rompe").
    // target="_blank" sobre el <form> solo (sin window.open primero) puede
    // degradar a navegar la MISMA pestaña si el navegador no lo reconoce
    // como gesto directo del usuario -- window.open() de entrada, todavía
    // dentro del mismo click, es la forma confiable de garantizar pestaña
    // nueva de verdad. Con una pestaña real, ESTA pestaña con el form
    // nunca se toca -- nada que perder ni que reconstruir al volver,
    // "Volver" en la preview solo cierra esa pestaña (ver base_exam_preview.html).
    const windowName = 'examTemplatePreview_' + Date.now();
    const previewWindow = window.open('', windowName);
    if (!previewWindow) {
        alert('El navegador bloqueó la ventana de previsualización. Habilitá las ventanas emergentes para este sitio e intentá de nuevo.');
        return;
    }

    const tempForm = document.createElement('form');
    tempForm.method = 'POST';
    tempForm.action = '/exam-templates/preview/';
    tempForm.target = windowName;
    tempForm.style.display = 'none';
    for (const [key, value] of formData.entries()) {
        if (value instanceof File) continue; // no hay campos de archivo en este form, pero por las dudas
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = value;
        tempForm.appendChild(input);
    }
    document.body.appendChild(tempForm);
    tempForm.submit();
    document.body.removeChild(tempForm);

    // Feedback breve en el botón (la pestaña nueva abre casi al instante,
    // no hay una promesa que esperar como con fetch).
    const btn = document.querySelector('button[onclick="previewExamTemplate()"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-check"></i> Abierto en pestaña nueva';
    btn.disabled = true;
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }, 1500);
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
    const saveAsCopyBtn = document.getElementById('save-as-copy-btn');
    if (!saveBtn) return;

    // Función de notificación tipo toast y scroll arriba
    const showNotification = (message, type = 'success') => {
    // Scroll arriba absoluto de la página
    window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
        // Toast Bootstrap
        const toastEl = document.getElementById('successToast');
        const toastMsg = document.getElementById('toastMessage');
        toastMsg.textContent = message;
        toastEl.className = `toast align-items-center text-bg-${type} border-0`;
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    };

    // Un solo handler para los dos botones (Guardar / Guardar como copia):
    // difieren solo en save_mode. 'update' pisa la plantilla que se está
    // editando (template_id, ya viene en el form como hidden field);
    // 'copy' siempre crea una fila nueva — es el comportamiento de antes,
    // ahora explícito en vez de ser lo único que existía.
    async function handleSave(btn, saveMode) {
        const form = document.getElementById('examTemplateForm');
        const formData = new FormData(form);
        formData.set('save_mode', saveMode);

        // Agregar todos los campos posibles (sin validación)
        const optionalFields = {
            'exam_mode': document.getElementById('id_exam_mode')?.value || '',
            'learning_outcomes': Array.from(document.querySelectorAll('.outcome-checkbox:checked'))
                                .map(cb => cb.value).join(','),
            'rubrics': Array.from(document.querySelectorAll('.rubric-checkbox:checked'))
                                .map(cb => cb.value).join(',')
        };

        // Agregar campos opcionales al FormData
        Object.entries(optionalFields).forEach(([key, value]) => {
            formData.append(key, value);
        });

        // Estado de carga
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
        btn.disabled = true;
        if (saveAsCopyBtn) saveAsCopyBtn.disabled = true;
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

            // En modo edición (update o copia) el destino natural es el
            // listado de plantillas — quedarse en un form de "Crear" recién
            // guardado confunde. Al crear desde cero (sin template_id) se
            // mantiene el destino de siempre.
            const isEditFlow = formData.has('template_id') && formData.get('template_id');
            showNotification(saveMode === 'update' ? 'Plantilla actualizada correctamente' : 'Plantilla guardada correctamente');
            setTimeout(function() {
                window.location.href = isEditFlow ? '/exam-templates/' : '/create-exam-template/';
            }, 1200); // 1.2 segundos para que el usuario vea el mensaje y se recargue la página
        } catch (error) {
            console.error('Error:', error);
            showNotification(error.message, 'danger');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
            if (saveAsCopyBtn) saveAsCopyBtn.disabled = false;
            saveBtn.disabled = false;
        }
    }

    saveBtn.addEventListener('click', function(e) {
        e.preventDefault();
        handleSave(saveBtn, saveBtn.dataset.saveMode || 'copy');
    });
    if (saveAsCopyBtn) {
        saveAsCopyBtn.addEventListener('click', function(e) {
            e.preventDefault();
            handleSave(saveAsCopyBtn, 'copy');
        });
    }
}


// Asegúrate de que esta línea esté al final del DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // ... (tu código existente) ...
    setupSaveTemplate();
});

