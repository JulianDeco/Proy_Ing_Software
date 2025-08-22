# archivo: 0018_crear_modelos_calendario.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('academico', '0017_asistencia'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnioAcademico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField()),
                ('activo', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Año Académico',
                'verbose_name_plural': 'Años Académicos',
            },
        ),
        migrations.CreateModel(
            name='CalendarioAcademico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('es_dia_clase', models.BooleanField(default=True)),
                ('descripcion', models.CharField(blank=True, max_length=200, null=True)),
                ('anio_academico', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='academico.anioacademico')),
            ],
            options={
                'verbose_name': 'Calendario Académico',
                'verbose_name_plural': 'Calendario Académico',
                'unique_together': {('anio_academico', 'fecha')},
            },
        ),
        migrations.AddField(
            model_name='comision',
            name='anio_academico',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, 
                to='academico.anioacademico'
            ),
        ),
    ]