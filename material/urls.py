from django.urls import path
from . import views as material_views  # Usar el mismo alias para todas las vistas

app_name = 'material'

urlpatterns = [
    path('', material_views.index, name='index'),
    path('upload/', material_views.upload_contenido, name='upload_contenido'),
    path('questions/<int:contenido_id>/', material_views.generate_questions, name='generate_questions'),
    path('review-questions/<int:contenido_id>/', material_views.review_questions, name='review_questions'),
    path('save-questions/<int:contenido_id>/', material_views.save_selected_questions, name='save_selected_questions'),
    path('create-exam/', material_views.create_exam, name='create_exam'),
    path('create-exam-template/', material_views.create_exam_template, name='create_exam_template'),
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
    path('logros/', material_views.manage_learning_outcomes, name='manage_learning_outcomes'),
    path('instituciones/eliminar/<int:pk>/', material_views.delete_institution, name='delete_institution'),
    path('instituciones/editar/<int:pk>/', material_views.edit_institution, name='edit_institution'),

#crud preguntas
    path('get-topics/', material_views.get_topics, name='get_topics'),
    path('get-subtopics/', material_views.get_subtopics, name='get_subtopics'),




# instituciones v2
    path('instituciones-v2/', material_views.institution_v2_list, name='institution_v2_list'),
    path('instituciones-v2/crear/', material_views.create_institution_v2, name='create_institution_v2'),
    path('instituciones-v2/editar/<int:pk>/', material_views.edit_institution_v2, name='edit_institution_v2'),
    path('instituciones-v2/eliminar/<int:pk>/', material_views.delete_institution_v2, name='delete_institution_v2'),
    path('instituciones-v2/favorito/<int:pk>/', material_views.toggle_favorite_institution, name='toggle_favorite_institution'),
    path('instituciones-v2/detalle/<int:pk>/', material_views.institution_v2_detail, name='institution_v2_detail'),
    path('instituciones-v2/logs/<int:pk>/', material_views.institution_v2_logs, name='institution_v2_logs'),
    # path('instituciones-v2/count-favorites/', material_views.count_favorite_institutions, name='count_favorite_institutions'),
    path('instituciones-v2/<int:institution_id>/campus/create/', material_views.create_campus_v2, name='create_campus_v2'),
    path('instituciones-v2/<int:institution_id>/campus/<int:campus_id>/edit/', material_views.edit_campus_v2, name='edit_campus_v2'),
    path('instituciones-v2/<int:institution_id>/campus/<int:campus_id>/delete/', material_views.delete_campus_v2, name='delete_campus_v2'),
    path('instituciones-v2/<int:institution_id>/facultad/create/', material_views.create_faculty_v2, name='create_faculty_v2'),
    path('instituciones-v2/<int:institution_id>/facultad/<int:faculty_id>/edit/', material_views.edit_faculty_v2, name='edit_faculty_v2'),
    path('instituciones-v2/<int:institution_id>/facultad/<int:faculty_id>/delete/', material_views.delete_faculty_v2, name='delete_faculty_v2'),
    path('instituciones-v2/<int:pk>/eliminar-logo/', material_views.delete_institution_logo_v2, name='delete_institution_logo_v2'),
    path('api/create-related-element/', material_views.create_related_element, name='create_related_element'),
path('instituciones/', material_views.manage_institutions, name='manage_institutions'),

# Subjects CRUD
path('subjects/', material_views.subject_list, name='subject_list'),
path('subjects/create/', material_views.create_subject, name='create_subject'),
path('subjects/<int:pk>/edit/', material_views.edit_subject, name='edit_subject'),
path('subjects/<int:pk>/delete/', material_views.delete_subject, name='delete_subject'),
path('subjects/<int:pk>/', material_views.SubjectDetailView.as_view(), name='subject_detail'),  

# Careers CRUD
# urls.py
path('careers/', material_views.career_list, name='career_list'),
path('careers/create/', material_views.career_create_simple, name='career_create_simple'),
path('careers/<int:pk>/associations/', material_views.career_associations, name='career_associations'),
path('careers/<int:pk>/edit/', material_views.edit_career, name='edit_career'),
path('careers/<int:pk>/delete/', material_views.delete_career, name='delete_career'),
path('careers/<int:pk>/', material_views.CareerDetailView.as_view(), name='career_detail'),

path('get_faculties_by_institution/<int:institution_id>/', material_views.get_faculties_by_institution, name='get_faculties_by_institution'),
path('get_campuses_by_institution/<int:institution_id>/', material_views.get_campuses_by_institution, name='get_campuses_by_institution'),

path('get-learning-outcomes/', material_views.get_learning_outcomes, name='get_learning_outcomes'),

]