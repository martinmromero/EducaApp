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
