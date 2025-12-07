from django.db import migrations, models
import django.db.models.deletion


def populate_tournament_from_match(apps, schema_editor):
    Report = apps.get_model("tournaments", "Report")
    for report in Report.objects.all().select_related("match"):
        if report.match and not report.tournament_id:
            report.tournament_id = report.match.tournament_id
            report.save(update_fields=["tournament"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0006_match_result_submitted_by_match_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="tournament",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to="tournaments.tournament"),
        ),
        migrations.AlterField(
            model_name="report",
            name="match",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="tournaments.match"),
        ),
        migrations.RunPython(populate_tournament_from_match, noop_reverse),
        migrations.AlterField(
            model_name="report",
            name="tournament",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tournaments.tournament"),
        ),
    ]
