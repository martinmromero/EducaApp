// create_exam.js
// JS para el formulario de creación de examen

document.addEventListener('DOMContentLoaded', function() {
    let questionsFetchToken = 0;

    function getSelectedTopicIds() {
        var topicsSelect = document.getElementById('id_topics');
        if (!topicsSelect) return [];
        return Array.from(topicsSelect.options)
            .filter(function(opt) { return opt.selected && opt.value !== 'all'; })
            .map(function(opt) { return opt.value; });
    }

    function syncTopicsSelectFromCheckboxes() {
        var topicsSelect = document.getElementById('id_topics');
        var container = document.getElementById('topics_checkbox_container');
        if (!topicsSelect || !container) return;

        var checkedIds = Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
            .map(function(cb) { return cb.dataset.topicValue; });

        Array.from(topicsSelect.options).forEach(function(opt) {
            opt.selected = checkedIds.includes(opt.value);
        });
    }

    function syncQuestionsSelectFromCheckboxes() {
        var questionsSelect = document.getElementById('id_questions');
        var container = document.getElementById('questions_checkbox_container');
        if (!questionsSelect || !container) return;

        var checkedIds = Array.from(container.querySelectorAll('input[type="checkbox"]:checked'))
            .map(function(cb) { return cb.dataset.questionValue; });

        Array.from(questionsSelect.options).forEach(function(opt) {
            opt.selected = checkedIds.includes(opt.value);
        });
    }

    function loadQuestionsBySelectedTopics() {
        var selectedTopics = getSelectedTopicIds();
        var questionsSelect = document.getElementById('id_questions');
        var subjectId = document.getElementById('id_subject')?.value;
        if (!questionsSelect || !subjectId) return;

        if (!selectedTopics.length) {
            questionsSelect.innerHTML = '';
            renderQuestionsCheckboxes();
            return;
        }

        var previouslySelected = Array.from(questionsSelect.options)
            .filter(function(opt) { return opt.selected; })
            .map(function(opt) { return String(opt.value); });

        // Al precargar un examen para editar, las preguntas objetivo llegan
        // via window.EXAM_PREFILL_QUESTIONS *antes* de que este fetch corra
        // (dispara el 'change' de temas). Sin esto, el fetch reconstruye las
        // opciones usando el snapshot vacio de arriba y pisa la seleccion
        // que el script de precarga intenta aplicar despues.
        if (window.EXAM_PREFILL_QUESTIONS && window.EXAM_PREFILL_QUESTIONS.length) {
            var prefillIds = window.EXAM_PREFILL_QUESTIONS.map(String);
            prefillIds.forEach(function(id) {
                if (!previouslySelected.includes(id)) previouslySelected.push(id);
            });
        }

        questionsFetchToken += 1;
        var currentToken = questionsFetchToken;

        var url = '/get-questions-by-topics/?topics=' + selectedTopics.join(',') + '&subject_id=' + subjectId;

        fetch(url)
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (currentToken !== questionsFetchToken) return;
                questionsSelect.innerHTML = '';
                data.forEach(function(question) {
                    var option = document.createElement('option');
                    option.value = question.id;
                    option.textContent = question.text;
                    option.selected = previouslySelected.includes(String(question.id));
                    questionsSelect.appendChild(option);
                });
                renderQuestionsCheckboxes();
                window.EXAM_PREFILL_QUESTIONS = null;
            });
    }

    function renderTopicsCheckboxes() {
        var topicsSelect = document.getElementById('id_topics');
        var container = document.getElementById('topics_checkbox_container');
        if (!topicsSelect || !container) return;

        container.innerHTML = '';
        Array.from(topicsSelect.options).filter(function(option) { return option.value !== 'all'; }).forEach(function(option) {
            var row = document.createElement('div');
            row.className = 'form-check mb-1';
            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'form-check-input';
            cb.id = 'topic_cb_' + option.value;
            cb.checked = option.selected;
            cb.dataset.topicValue = option.value;

            var label = document.createElement('label');
            label.className = 'form-check-label';
            label.htmlFor = cb.id;
            label.textContent = option.textContent;

            cb.addEventListener('change', function() {
                syncTopicsSelectFromCheckboxes();
                loadQuestionsBySelectedTopics();
            });

            row.appendChild(cb);
            row.appendChild(label);
            container.appendChild(row);
        });
    }

    function renderQuestionsCheckboxes() {
        var questionsSelect = document.getElementById('id_questions');
        var container = document.getElementById('questions_checkbox_container');
        if (!questionsSelect || !container) return;

        container.innerHTML = '';
        Array.from(questionsSelect.options).forEach(function(option) {
            var row = document.createElement('div');
            row.className = 'form-check mb-1';

            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'form-check-input';
            cb.id = 'question_cb_' + option.value;
            cb.checked = option.selected;
            cb.dataset.questionValue = option.value;

            var label = document.createElement('label');
            label.className = 'form-check-label';
            label.htmlFor = cb.id;
            label.textContent = option.textContent;

            cb.addEventListener('change', function() {
                syncQuestionsSelectFromCheckboxes();
            });

            row.appendChild(cb);
            row.appendChild(label);
            container.appendChild(row);
        });
    }

    function updateSuggestedBatchName() {
        var batchInput = document.getElementById('batch_name');
        if (!batchInput || batchInput.dataset.userEdited === '1') return;

        var tipo = document.querySelector('input[name="tipo_examen"]:checked')?.value || 'examen';
        var subject = document.getElementById('id_subject');
        var institution = document.getElementById('institucion_dropdown');
        var semester = document.getElementById('batch_semester')?.value || 'sin cuatrimestre';
        var versions = document.getElementById('num_versions')?.value || '1';
        var fecha = document.getElementById('fecha')?.value || '';
        var year = fecha ? fecha.split('-')[0] : 'sin anio';

        var tipoLabelMap = {
            '1er_parcial': '1er parcial',
            '2do_parcial': '2do parcial',
            '3er_parcial': '3er parcial',
            'final': 'final',
            'recuperatorio': 'recuperatorio',
            'practico': 'practico'
        };
        var tipoLabel = tipoLabelMap[tipo] || 'examen';
        var subjectLabel = subject && subject.selectedOptions[0] ? subject.selectedOptions[0].textContent : 'sin materia';
        var institutionLabel = institution && institution.selectedOptions[0] ? institution.selectedOptions[0].textContent : 'sin institucion';

        batchInput.value = `${tipoLabel} - ${subjectLabel} - ${institutionLabel} - ${semester} - ${year} - ${versions} opciones`;
    }

    var batchNameInput = document.getElementById('batch_name');
    if (batchNameInput) {
        batchNameInput.addEventListener('input', function() {
            this.dataset.userEdited = this.value.trim() ? '1' : '0';
        });
    }

    // Autocompletar campos al seleccionar una plantilla
    var plantillaSelect = document.getElementById('plantilla');
    plantillaSelect.addEventListener('change', function() {
        var plantillaId = this.value;
            if (!plantillaId) {
                location.reload();
                return;
            }
            if (plantillaId) {
            fetch('/get-exam-template/' + plantillaId + '/')
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    // Materia
                    if (data.subject_id) {
                        var subjectSelect = document.getElementById('id_subject');
                        subjectSelect.value = data.subject_id;
                        subjectSelect.dispatchEvent(new Event('change'));
                    }
                    // Institución
                    if (data.institution_id) {
                        var institucionSelect = document.getElementById('institucion_dropdown');
                        institucionSelect.value = data.institution_id;
                        institucionSelect.dispatchEvent(new Event('change'));
                    }
                    // Esperar a que los dropdowns dependientes se llenen
                    setTimeout(function() {
                        // Facultad
                        if (data.faculty_id) {
                            var facultadSelect = document.getElementById('facultad_dropdown');
                            facultadSelect.value = data.faculty_id;
                            facultadSelect.dispatchEvent(new Event('change'));
                            // Esperar a que el dropdown de carrera se llene por la cascada
                            setTimeout(function() {
                                if (data.career_id) {
                                    var carreraSelect = document.getElementById('carrera_dropdown');
                                    var found = false;
                                    Array.from(carreraSelect.options).forEach(function(option) {
                                        if (option.value == data.career_id) {
                                            found = true;
                                        }
                                    });
                                    if (!found) {
                                        // Buscar el nombre de la carrera por AJAX y agregarla como opción temporal
                                        fetch('/get-career-name/' + data.career_id + '/')
                                            .then(function(response) { return response.json(); })
                                            .then(function(careerData) {
                                                var option = document.createElement('option');
                                                option.value = data.career_id;
                                                option.textContent = careerData.name + ' (no asociada)';
                                                option.selected = true;
                                                carreraSelect.appendChild(option);
                                            });
                                    } else {
                                        carreraSelect.value = data.career_id;
                                    }
                                }
                            }, 400);
                        }
                        // Sede
                        if (data.campus_id) {
                            var sedeSelect = document.getElementById('sede_dropdown');
                            sedeSelect.value = data.campus_id;
                        }
                        // Temas evaluados
                        if (data.topics && Array.isArray(data.topics)) {
                            var topicsSelect = document.getElementById('id_topics');
                            if (topicsSelect) {
                                Array.from(topicsSelect.options).forEach(function(option) {
                                    option.selected = data.topics.includes(parseInt(option.value));
                                });
                            }
                        }
                        // Resultados de aprendizaje
                        if (data.learning_outcomes && Array.isArray(data.learning_outcomes)) {
                            var outcomesContainer = document.getElementById('learning_outcomes_container');
                            if (outcomesContainer) {
                                Array.from(outcomesContainer.querySelectorAll('input[type="checkbox"]')).forEach(function(checkbox) {
                                    checkbox.checked = data.learning_outcomes.includes(parseInt(checkbox.value));
                                });
                            }
                        }
                        // Preguntas
                        if (data.questions && Array.isArray(data.questions)) {
                            var questionsSelect = document.getElementById('id_questions');
                            if (questionsSelect) {
                                Array.from(questionsSelect.options).forEach(function(option) {
                                    option.selected = data.questions.includes(parseInt(option.value));
                                });
                            }
                        }
                        // Profesor
                        if (data.professor_id) {
                            var profesorSelect = document.getElementById('profesor_dropdown');
                            profesorSelect.value = data.professor_id;
                        }
                        // Tipo de examen
                        if (data.exam_type) {
                            var tipoExamenSelect = document.getElementById('tipo_examen');
                            tipoExamenSelect.value = data.exam_type;
                        }
                        // Modalidad de examen
                        if (data.exam_mode) {
                            var tipoModalidadSelect = document.getElementById('tipo_modalidad');
                            tipoModalidadSelect.value = data.exam_mode;
                        }
                        // Turno
                        if (data.shift) {
                            var turnoSelect = document.getElementById('turno_dropdown');
                            turnoSelect.value = data.shift;
                        }
                    }, 600); // Espera 600ms para asegurar que los campos se llenen
                    // Título
                    if (data.title) {
                        var titleInput = document.getElementById('id_title');
                        if (titleInput) titleInput.value = data.title;
                    }
                    // Instrucciones
                    if (data.instructions) {
                        var instructionsInput = document.getElementById('id_instructions');
                        if (instructionsInput) instructionsInput.value = data.instructions;
                    }
                    // Duración
                    if (data.duration_minutes) {
                        var durationInput = document.getElementById('id_duration_minutes');
                        if (durationInput) durationInput.value = data.duration_minutes;
                    }
                });
        }
    });
    // Temas evaluados según materia seleccionada
    var subjectSelect = document.getElementById('id_subject');
    var topicsSelect = document.getElementById('id_topics');
    subjectSelect.addEventListener('change', function() {
        var subjectId = this.value;
        // Limpiar selects de temas y preguntas
        topicsSelect.innerHTML = '';
        var questionsSelect = document.getElementById('id_questions');
        if (questionsSelect) {
            questionsSelect.innerHTML = '';
        }
        // Temas evaluados
        fetch('/get-topics/?subject_id=' + subjectId)
            .then(function(response) { return response.json(); })
            .then(function(data) {
                data.forEach(function(topic) {
                    var option = document.createElement('option');
                    option.value = topic.id;
                    option.textContent = topic.name;
                    topicsSelect.appendChild(option);
                });
                renderTopicsCheckboxes();
                var questionsContainer = document.getElementById('questions_checkbox_container');
                if (questionsContainer) questionsContainer.innerHTML = '';
            });
        // Resultados de aprendizaje como checkboxes
        fetch('/get-learning-outcomes/?subject_id=' + subjectId)
            .then(function(response) { return response.json(); })
            .then(function(data) {
                var container = document.getElementById('learning_outcomes_container');
                container.innerHTML = '';
                data.forEach(function(outcome) {
                    var div = document.createElement('div');
                    div.className = 'form-check';
                    var checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'form-check-input';
                    checkbox.name = 'learning_outcomes';
                    checkbox.value = outcome.id;
                    checkbox.id = 'outcome_' + outcome.id;
                    var label = document.createElement('label');
                    label.className = 'form-check-label';
                    label.htmlFor = checkbox.id;
                    label.textContent = outcome.description;
                    div.appendChild(checkbox);
                    div.appendChild(label);
                    container.appendChild(div);
                });
            });
    });

    // Compatibilidad: si alguien cambia el select oculto manualmente
    topicsSelect.addEventListener('change', function() {
        renderTopicsCheckboxes();
        loadQuestionsBySelectedTopics();
    });

    document.getElementById('topics_select_all')?.addEventListener('click', function() {
        var container = document.getElementById('topics_checkbox_container');
        if (!container) return;
        container.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = true; });
        syncTopicsSelectFromCheckboxes();
        loadQuestionsBySelectedTopics();
    });

    document.getElementById('topics_select_none')?.addEventListener('click', function() {
        var container = document.getElementById('topics_checkbox_container');
        if (!container) return;
        container.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = false; });
        syncTopicsSelectFromCheckboxes();
        loadQuestionsBySelectedTopics();
    });

    document.getElementById('questions_select_all')?.addEventListener('click', function() {
        var container = document.getElementById('questions_checkbox_container');
        if (!container) return;
        container.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = true; });
        syncQuestionsSelectFromCheckboxes();
    });

    document.getElementById('questions_select_none')?.addEventListener('click', function() {
        var container = document.getElementById('questions_checkbox_container');
        if (!container) return;
        container.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = false; });
        syncQuestionsSelectFromCheckboxes();
    });

    // Cascada institución → facultad → carrera y sede
    var institucionSelect = document.getElementById('institucion_dropdown');
    var facultadSelect = document.getElementById('facultad_dropdown');
    var carreraSelect = document.getElementById('carrera_dropdown');
    var sedeSelect = document.getElementById('sede_dropdown');

    institucionSelect.addEventListener('change', function() {
        var institucionId = this.value;
        facultadSelect.innerHTML = '<option value="">Seleccionar facultad</option><option value="otro">Otro</option>';
        carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
        sedeSelect.innerHTML = '<option value="">Seleccionar sede</option><option value="otro">Otro</option>';
        if (!institucionId || !/^\d+$/.test(institucionId)) {
            return;
        }
        // Filtrar facultades por institución
        fetch('/get_faculties_by_institution/' + institucionId + '/')
            .then(function(response) { return response.json(); })
            .then(function(data) {
                facultadSelect.innerHTML = '<option value="">Seleccionar facultad</option><option value="otro">Otro</option>';
                if (data.faculties) {
                    data.faculties.forEach(function(facultad) {
                        var option = document.createElement('option');
                        option.value = facultad.id;
                        option.textContent = facultad.name;
                        facultadSelect.appendChild(option);
                    });
                }
            });
        // Filtrar sedes por institución
        fetch('/get_campuses_by_institution/' + institucionId + '/')
            .then(function(response) { return response.json(); })
            .then(function(data) {
                sedeSelect.innerHTML = '<option value="">Seleccionar sede</option><option value="otro">Otro</option>';
                if (data.campuses) {
                    data.campuses.forEach(function(sede) {
                        var option = document.createElement('option');
                        option.value = sede.id;
                        option.textContent = sede.name;
                        sedeSelect.appendChild(option);
                    });
                }
            });
    });

    facultadSelect.addEventListener('change', function() {
        var facultadId = this.value;
        if (!facultadId || !/^\d+$/.test(facultadId)) {
            carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
            return;
        }
        // Filtrar carreras por facultad
        fetch('/get-careers-by-faculty/' + facultadId + '/')
            .then(function(response) { return response.json(); })
            .then(function(data) {
                carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
                if (data.careers) {
                    data.careers.forEach(function(carrera) {
                        var option = document.createElement('option');
                        option.value = carrera.id;
                        option.textContent = carrera.name;
                        carreraSelect.appendChild(option);
                    });
                }
            });
    });

    ['change', 'input'].forEach(function(evtName) {
        document.getElementById('id_subject')?.addEventListener(evtName, updateSuggestedBatchName);
        document.getElementById('institucion_dropdown')?.addEventListener(evtName, updateSuggestedBatchName);
        document.getElementById('batch_semester')?.addEventListener(evtName, updateSuggestedBatchName);
        document.getElementById('num_versions')?.addEventListener(evtName, updateSuggestedBatchName);
        document.getElementById('fecha')?.addEventListener(evtName, updateSuggestedBatchName);
        document.querySelectorAll('input[name="tipo_examen"]').forEach(function(radio) {
            radio.addEventListener(evtName, updateSuggestedBatchName);
        });
    });

    updateSuggestedBatchName();
    renderTopicsCheckboxes();
    renderQuestionsCheckboxes();
});

function toggleTextbox(selectId, textboxId) {
    var select = document.getElementById(selectId);
    var textbox = document.getElementById(textboxId);
    if (select.value === 'otro') {
        textbox.style.display = 'block';
    } else {
        textbox.style.display = 'none';
    }
}
