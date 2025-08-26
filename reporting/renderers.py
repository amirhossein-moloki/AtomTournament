import csv
from io import StringIO
from rest_framework.renderers import BaseRenderer

class CSVRenderer(BaseRenderer):
    media_type = 'text/csv'
    format = 'csv'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders report data into CSV format.
        This is a simplified implementation that handles a specific report structure.
        """
        if not data:
            return ''

        string_buffer = StringIO()
        writer = csv.writer(string_buffer)

        # Heuristic to determine which report we're rendering
        if 'summary' in data and 'total_revenue' in data['summary']:
            self.render_revenue_report(writer, data)
        elif 'summary' in data and 'active_players' in data['summary']:
            self.render_players_report(writer, data)
        # Add other report types here
        else:
            # Fallback for unknown structure
            writer.writerow(['Error'])
            writer.writerow(['Unsupported data structure for CSV export.'])

        return string_buffer.getvalue()

    def render_revenue_report(self, writer, data):
        # Summary
        writer.writerow(['Revenue Report Summary'])
        summary = data.get('summary', {})
        writer.writerow(['Total Revenue', summary.get('total_revenue')])
        writer.writerow(['Platform Share', summary.get('platform_share')])
        writer.writerow(['Players Share', summary.get('players_share')])
        writer.writerow([]) # Spacer

        # By Tournament
        writer.writerow(['Revenue by Tournament'])
        writer.writerow(['Tournament Name', 'Total Revenue'])
        for item in data.get('by_tournament', []):
            writer.writerow([item.get('tournament_name'), item.get('total_revenue')])
        writer.writerow([])

        # By Game
        writer.writerow(['Revenue by Game'])
        writer.writerow(['Game Name', 'Total Revenue'])
        for item in data.get('by_game', []):
            writer.writerow([item.get('game_name'), item.get('total_revenue')])
        writer.writerow([])

    def render_players_report(self, writer, data):
        # Summary
        writer.writerow(['Players Report Summary'])
        summary = data.get('summary', {})
        writer.writerow(['Total Users', summary.get('total_users')])
        writer.writerow(['Active Players', summary.get('active_players')])
        writer.writerow(['Avg Participation', summary.get('avg_participation_per_player')])
        writer.writerow([])

        # Distribution by Game
        writer.writerow(['Player Distribution by Game'])
        writer.writerow(['Game Name', 'Player Count', 'Percentage'])
        for item in data.get('distribution_by_game', []):
            writer.writerow([
                item.get('game_name'),
                item.get('player_count'),
                item.get('percentage')
            ])
        writer.writerow([])
