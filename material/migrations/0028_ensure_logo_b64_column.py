from django.db import migrations


def ensure_logo_b64_column(apps, schema_editor):
    table_name = 'material_institutionv2'
    column_name = 'logo_b64'

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = [col.name for col in connection.introspection.get_table_description(cursor, table_name)]

    if column_name not in columns:
        schema_editor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT NULL')


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0027_add_logo_b64_to_institutionv2'),
    ]

    operations = [
        migrations.RunPython(ensure_logo_b64_column, migrations.RunPython.noop),
    ]
