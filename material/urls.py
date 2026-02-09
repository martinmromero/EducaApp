from django.urls import path
from . import views as material_views  # Usar el mismo alias para todas las vistas
from . import views_document_processor as doc_views  # Importar vistas del procesador de documentos

app_name = 'material'

urlpatterns = [
    path('preview-exam/', material_views.preview_exam, name='preview_exam'),
    path('', material_views.index, name='index'),
    path('get-career-name/<int:career_id>/', material_views.get_career_name, name='get_career_name'),
    path('upload/', material_views.upload_contenido, name='upload_contenido'),
    path('extract-metadata/', material_views.extract_metadata_from_upload, name='extract_metadata_from_upload'),
    path('questions/<int:contenido_id>/', material_views.generate_questions, name='generate_questions'),
    path('review-questions/<int:contenido_id>/', material_views.review_questions, name='review_questions'),
    path('save-questions/<int:contenido_id>/', material_views.save_selected_questions, name='save_selected_questions'),
    path('create-exam/', material_views.create_exam, name='create_exam'),
    path('create-exam-template/', material_views.create_exam_template, name='create_exam_template'),
    path('exam-templates/edit/<int:template_id>/', material_views.edit_exam_template, name='edit_exam_template'),
    path('exam-templates/preview/', material_views.preview_exam_template, name='preview_exam_template'),
    path('exam-templates/', material_views.list_exam_templates, name='list_exam_templates'),
    path('exam-templates/delete/', material_views.delete_exam_template, name='delete_exam_template'),
    path('exam-templates/save/', material_views.save_exam_template, name='save_exam_template'),
    path('signup/', material_views.signup, name='signup'),
    path('users/', material_views.user_list, name='user_list'),
    path('users/edit/<int:user_id>/', material_views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', material_views.delete_user, name='delete_user'),
    path('mis-datos/', material_views.mis_datos, name='mis_datos'),
    path('mis-examenes/', material_views.mis_examenes, name='mis_examenes'),
    path('lista-preguntas/', material_views.lista_preguntas, name='lista_preguntas'),
    path('mis-contenidos/', material_views.mis_contenidos, name='mis_contenidos'),
    path('delete-contenido/', material_views.delete_contenido, name='delete_contenido'),
    path('upload-questions/', material_views.upload_questions, name='upload_questions'),
    path('download-template/<str:format>/', material_views.download_template, name='download_template'),
    path('editar-pregunta/<int:pk>/', material_views.editar_pregunta, name='editar_pregunta'),
    path('eliminar-pregunta/<int:pk>/', material_views.eliminar_pregunta, name='eliminar_pregunta'),
#crud preguntas
    path('get-topics/', material_views.get_topics, name='get_topics'),
    path('get-subtopics/', material_views.get_subtopics, name='get_subtopics'),
    
# AJAX endpoints para carreras
    path('get-faculties/', material_views.get_faculties, name='get_faculties'),
    path('get-campus/', material_views.get_campus_by_institution, name='get_campus_by_institution'),

# Document Processor - Nuevas URLs para procesamiento avanzado de documentos
    path('doc-processor/', doc_views.document_processor_dashboard, name='document_processor_dashboard'),
    path('doc-processor/upload/', doc_views.upload_and_process_document, name='upload_and_process_document'),
    path('doc-processor/count-tokens/', doc_views.count_document_tokens, name='count_document_tokens'),
    path('doc-processor/split-chunks/', doc_views.split_text_chunks, name='split_text_chunks'),
    path('doc-processor/optimize/', doc_views.optimize_text_view, name='optimize_text'),
    
    # Local AI Server integration
    path('doc-processor/local-ai/status/', doc_views.check_local_ai_status, name='check_local_ai_status'),
    path('doc-processor/local-ai/models/', doc_views.list_local_ai_models, name='list_local_ai_models'),
    path('doc-processor/local-ai/set-model/', doc_views.set_local_ai_model, name='set_local_ai_model'),
    
    # AI Question Generation
    path('doc-processor/generate-questions/', doc_views.generate_questions_from_chapters, name='generate_questions_from_chapters'),
    path('doc-processor/save-questions/', doc_views.save_generated_questions, name='save_generated_questions'),




# instituciones v2
    path('instituciones-v2/', material_views.institution_v2_list, name='institution_v2_list'),
    path('instituciones-v2/crear/', material_views.create_institution_v2, name='create_institution_v2'),
    path('instituciones-v2/editar/<int:pk>/', material_views.edit_institution_v2, name='edit_institution_v2'),
    path('instituciones-v2/eliminar/<int:pk>/', material_views.delete_institution_v2, name='delete_institution_v2'),
    path('instituciones-v2/favorito/<int:pk>/', material_views.toggle_favorite_institution, name='toggle_favorite_institution'),
    path('instituciones-v2/detalle/<int:pk>/', material_views.institution_v2_detail, name='institution_v2_detail'),
    path('instituciones-v2/logs/<int:pk>/', material_views.institution_v2_logs, name='institution_v2_logs'),
# linea siguiente comentada para ser borrada:   
    # path('instituciones-v2/count-favorites/', material_views.count_favorite_institutions, name='count_favorite_institutions'),
    path('instituciones-v2/<int:institution_id>/campus/create/', material_views.create_campus_v2, name='create_campus_v2'),
    path('instituciones-v2/<int:institution_id>/campus/<int:campus_id>/edit/', material_views.edit_campus_v2, name='edit_campus_v2'),
    path('instituciones-v2/<int:institution_id>/campus/<int:campus_id>/delete/', material_views.delete_campus_v2, name='delete_campus_v2'),
    path('instituciones-v2/<int:institution_id>/facultad/create/', material_views.create_faculty_v2, name='create_faculty_v2'),
    path('instituciones-v2/<int:institution_id>/facultad/<int:faculty_id>/edit/', material_views.edit_faculty_v2, name='edit_faculty_v2'),
    path('instituciones-v2/<int:institution_id>/facultad/<int:faculty_id>/delete/', material_views.delete_faculty_v2, name='delete_faculty_v2'),
    path('instituciones-v2/<int:pk>/eliminar-logo/', material_views.delete_institution_logo_v2, name='delete_institution_logo_v2'),
    path('api/create-related-element/', material_views.create_related_element, name='create_related_element'),

# Subjects CRUD
path('subjects/', material_views.subject_list, name='subject_list'),
# linea siguiente obsoleta. si funciona dos renglones abajo, borrar 1 renglon abajo de subject create
#path('subjects/create/', material_views.create_subject, name='create_subject'),
path('subjects/create/', material_views.SubjectCreateView.as_view(), name='create_subject'),
# linea siguiente obsoleta. si funciona dos renglones abajo, borrar 1 renglon abajo de subject edit
#path('subjects/<int:pk>/edit/', material_views.edit_subject, name='edit_subject'),
path('subjects/<int:pk>/edit/', material_views.SubjectUpdateView.as_view(), name='edit_subject'),

path('subjects/<int:pk>/delete/', material_views.delete_subject, name='delete_subject'),
path('subjects/<int:pk>/', material_views.SubjectDetailView.as_view(), name='subject_detail'),  
path('subjects/<int:subject_id>/outcomes/', material_views.LearningOutcomeListView.as_view(), name='learningoutcome_list'),
path('subjects/<int:subject_id>/outcomes/add/', material_views.LearningOutcomeCreateView.as_view(), name='learningoutcome_add'),
path('outcomes/<int:pk>/edit/', material_views.LearningOutcomeUpdateView.as_view(), name='learningoutcome_edit'),
path('outcomes/<int:pk>/delete/', material_views.LearningOutcomeDeleteView.as_view(), name='learningoutcome_delete'),


# Careers CRUD
# urls.py
path('careers/', material_views.career_list, name='career_list'),
path('careers/create/', material_views.career_create_simple, name='career_create_simple'),
path('careers/<int:pk>/associations/', material_views.career_associations, name='career_associations'),
path('careers/<int:pk>/delete/', material_views.delete_career, name='delete_career'),
path('careers/<int:pk>/', material_views.CareerDetailView.as_view(), name='career_detail'),

path('get_faculties_by_institution/<int:institution_id>/', material_views.get_faculties_by_institution, name='get_faculties_by_institution'),
path('get_campuses_by_institution/<int:institution_id>/', material_views.get_campuses_by_institution, name='get_campuses_by_institution'),
path('exam-templates/view/<int:template_id>/', material_views.view_exam_template, name='view_exam_template'),


path('add-topic/', material_views.add_topic, name='add_topic'),
path('add-subtopic/', material_views.add_subtopic, name='add_subtopic'),

path('upload/', material_views.upload_contenido, name='upload_contenido'),  # Para contenido tradicional
path('upload-questions/', material_views.upload_questions, name='upload_questions'),  # Nueva vista mejorada

path('get-questions-by-topics/', material_views.get_questions_by_topics, name='get_questions_by_topics'),
path('get-careers-by-faculty/<int:faculty_id>/', material_views.get_careers_by_faculty, name='get_careers_by_faculty'),


path('get-exam-template/<int:template_id>/', material_views.get_exam_template, name='get_exam_template'),

#el siguiente renglon tal vez sea obsoleto. revisar cuando termine de ver temas de learning outcomes
path('get-learning-outcomes/', material_views.get_learning_outcomes, name='get_learning_outcomes'),

# Cuestionarios Orales
path('oral-exams/', material_views.list_oral_exams, name='list_oral_exams'),
path('oral-exams/create/', material_views.create_oral_exam, name='create_oral_exam'),
path('oral-exams/validate/', material_views.validate_oral_exam, name='validate_oral_exam'),
path('oral-exams/<int:exam_id>/', material_views.view_oral_exam, name='view_oral_exam'),
path('oral-exams/<int:exam_id>/delete/', material_views.delete_oral_exam, name='delete_oral_exam'),
path('oral-exams/evaluate/', material_views.evaluate_oral_question, name='evaluate_oral_question'),
path('oral-exams/assign-names/', material_views.assign_student_names, name='assign_student_names'),
path('oral-exams/available-questions/', material_views.get_available_questions, name='get_available_questions'),
path('oral-exams/exchange-question/', material_views.exchange_question, name='exchange_question'),

]