// create_exam.js
// JS para el formulario de creación de examen

document.addEventListener('DOMContentLoaded', function() {
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
                // Agregar opción 'Todos los temas' siempre
                var allOption = document.createElement('option');
                allOption.value = 'all';
                allOption.textContent = 'Todos los temas';
                topicsSelect.appendChild(allOption);
                data.forEach(function(topic) {
                    var option = document.createElement('option');
                    option.value = topic.id;
                    option.textContent = topic.name;
                    topicsSelect.appendChild(option);
                });
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

    // Filtrar preguntas por tema seleccionado
    topicsSelect.addEventListener('change', function() {
        var selectedTopics = Array.from(topicsSelect.selectedOptions).map(function(opt) { return opt.value; });
        var questionsSelect = document.getElementById('id_questions');
        if (selectedTopics.includes('all')) {
            // Mostrar todas las preguntas de la materia seleccionada
            var subjectId = document.getElementById('id_subject').value;
            fetch('/get-questions-by-topics/?all=true&subject_id=' + subjectId)
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    questionsSelect.innerHTML = '';
                    data.forEach(function(question) {
                        var option = document.createElement('option');
                        option.value = question.id;
                        option.textContent = question.text;
                        questionsSelect.appendChild(option);
                    });
                });
        } else {
            fetch('/get-questions-by-topics/?topics=' + selectedTopics.join(','))
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    questionsSelect.innerHTML = '';
                    data.forEach(function(question) {
                        var option = document.createElement('option');
                        option.value = question.id;
                        option.textContent = question.text;
                        questionsSelect.appendChild(option);
                    });
                });
        }
    });

    // Cascada institución → facultad → carrera y sede
    var institucionSelect = document.getElementById('institucion_dropdown');
    var facultadSelect = document.getElementById('facultad_dropdown');
    var carreraSelect = document.getElementById('carrera_dropdown');
    var sedeSelect = document.getElementById('sede_dropdown');

    institucionSelect.addEventListener('change', function() {
        var institucionId = this.value;
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
        // Limpiar carreras
        carreraSelect.innerHTML = '<option value="">Seleccionar carrera</option><option value="otro">Otro</option>';
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

// ── Prefill form from session data (when coming back from preview via "Editar") ──
document.addEventListener('DOMContentLoaded', function() {
    if (typeof EXAM_PREFILL === 'undefined' || !EXAM_PREFILL || !Object.keys(EXAM_PREFILL).length) return;
    var data = EXAM_PREFILL;

    function isNumeric(v) { return v && /^\d+$/.test(String(v)); }

    function setDropdownOrText(selectId, textId, value, customText) {
        var sel = document.getElementById(selectId);
        if (!sel) return;
        if (value === 'otro') {
            sel.value = 'otro';
            toggleTextbox(selectId, textId);
            var txt = document.getElementById(textId);
            if (txt && customText) txt.value = customText;
        } else if (value) {
            sel.value = value;
        }
    }

    // Static text inputs
    var staticMap = { 'fecha': 'fecha', 'curso': 'curso', 'id_duration_minutes': 'duration_minutes', 'id_instructions': 'instructions', 'id_title': 'title' };
    Object.keys(staticMap).forEach(function(elId) {
        var el = document.getElementById(elId);
        var val = data[staticMap[elId]];
        if (el && val) el.value = val;
    });

    // Radio buttons
    ['tipo_examen', 'tipo_modalidad'].forEach(function(name) {
        if (data[name]) {
            var r = document.querySelector('input[name="' + name + '"][value="' + data[name] + '"]');
            if (r) r.checked = true;
        }
    });

    // Checkboxes: modalidad_resolucion
    if (data.modalidad_resolucion && Array.isArray(data.modalidad_resolucion)) {
        data.modalidad_resolucion.forEach(function(val) {
            var cb = document.querySelector('input[name="modalidad_resolucion"][value="' + val + '"]');
            if (cb) cb.checked = true;
        });
    }

    // Turno and Profesor (static dropdowns)
    setDropdownOrText('turno_dropdown', 'turno_text', data.turno, data.turno_text);
    if (data.profesor && isNumeric(data.profesor)) {
        var profSel = document.getElementById('profesor_dropdown');
        if (profSel) profSel.value = data.profesor;
    }

    // Subject → triggers AJAX load of topics + learning_outcomes
    if (data.subject) {
        var subjSel = document.getElementById('id_subject');
        if (subjSel) {
            subjSel.value = data.subject;
            subjSel.dispatchEvent(new Event('change'));
        }
    }

    // Institution → triggers AJAX load of faculties + campuses
    if (data.institucion && isNumeric(data.institucion)) {
        var instSel = document.getElementById('institucion_dropdown');
        if (instSel) {
            instSel.value = data.institucion;
            instSel.dispatchEvent(new Event('change'));
        }
    }

    // After AJAX: set faculty, select topics, select learning_outcomes
    setTimeout(function() {
        // Faculty
        if (data.facultad) {
            var facSel = document.getElementById('facultad_dropdown');
            if (facSel) {
                if (data.facultad === 'otro') {
                    facSel.value = 'otro';
                    toggleTextbox('facultad_dropdown', 'facultad_text');
                    var ft = document.getElementById('facultad_text');
                    if (ft && data.facultad_text) ft.value = data.facultad_text;
                } else {
                    facSel.value = data.facultad;
                    if (isNumeric(data.facultad)) facSel.dispatchEvent(new Event('change'));
                }
            }
        }
        // Sede
        if (data.sede && isNumeric(data.sede)) {
            var sedeSel = document.getElementById('sede_dropdown');
            if (sedeSel) sedeSel.value = data.sede;
        }
        // Topics: select + trigger change (which loads questions)
        var topicsSel = document.getElementById('id_topics');
        if (topicsSel && data.topics && Array.isArray(data.topics)) {
            Array.from(topicsSel.options).forEach(function(opt) {
                opt.selected = data.topics.some(function(v) { return String(v) === opt.value; });
            });
            topicsSel.dispatchEvent(new Event('change'));
        }
        // Learning outcomes checkboxes
        if (data.learning_outcomes && Array.isArray(data.learning_outcomes)) {
            var loContainer = document.getElementById('learning_outcomes_container');
            if (loContainer) {
                Array.from(loContainer.querySelectorAll('input[type="checkbox"]')).forEach(function(cb) {
                    cb.checked = data.learning_outcomes.some(function(v) { return String(v) === cb.value; });
                });
            }
        }
    }, 700);

    // After topics AJAX loads questions: select them. Also set carrera.
    setTimeout(function() {
        if (data.carrera) {
            var carrSel = document.getElementById('carrera_dropdown');
            if (carrSel) {
                if (data.carrera === 'otro') {
                    carrSel.value = 'otro';
                    toggleTextbox('carrera_dropdown', 'carrera_text');
                    var ct = document.getElementById('carrera_text');
                    if (ct && data.carrera_text) ct.value = data.carrera_text;
                } else {
                    carrSel.value = data.carrera;
                }
            }
        }
        var qSel = document.getElementById('id_questions');
        if (qSel && data.questions && Array.isArray(data.questions)) {
            Array.from(qSel.options).forEach(function(opt) {
                opt.selected = data.questions.some(function(v) { return String(v) === opt.value; });
            });
        }
    }, 1400);
});
