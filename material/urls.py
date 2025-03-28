from django.urls import path
from . import views

app_name = 'material'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_material, name='upload_material'),
    path('questions/<int:material_id>/', views.generate_questions, name='generate_questions'),
    path('review-questions/<int:material_id>/', views.review_questions, name='review_questions'),
    path('save-questions/<int:material_id>/', views.save_selected_questions, name='save_selected_questions'),
    path('create-exam/', views.create_exam, name='create_exam'),
    path('create-exam-template/', views.create_exam_template, name='create_exam_template'),
    path('signup/', views.signup, name='signup'),
    path('users/', views.user_list, name='user_list'),
    path('users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('mis-datos/', views.mis_datos, name='mis_datos'),
    path('mis-examenes/', views.mis_examenes, name='mis_examenes'),
    path('lista-preguntas/', views.lista_preguntas, name='lista_preguntas'),
    path('mis-materiales/', views.mis_materiales, name='mis_materiales'),
    path('delete-material/', views.delete_material, name='delete_material'),
    path('upload-questions/', views.upload_questions, name='upload_questions'),
    path('download-template/<str:format>/', views.download_template, name='download_template'),
    path('create-exam-template/', views.create_exam_template, name='create_exam_template'),
    path('preview-exam-template/<int:template_id>/', views.preview_exam_template, name='preview_exam_template'),
    path('list-exam-templates/', views.list_exam_templates, name='list_exam_templates'),
    path('delete-exam-template/', views.delete_exam_template, name='delete_exam_template'),
    path('preguntas/<int:pk>/editar/', views.editar_pregunta, name='editar_pregunta'),
    path('preguntas/<int:pk>/eliminar/', views.eliminar_pregunta, name='eliminar_pregunta'),

]
