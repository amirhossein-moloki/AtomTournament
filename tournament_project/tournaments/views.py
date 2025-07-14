from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Match, Tournament
from .services import join_tournament, generate_matches


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_tournament_view(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    try:
        join_tournament(request.user, tournament)
        return Response({"message": "Successfully joined tournament."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_matches_view(request, pk):
    tournament = get_object_or_404(Tournament, pk=pk)
    if not request.user.is_staff:
        return Response(
            {"error": "You do not have permission to perform this action."}, status=403
        )
    try:
        generate_matches(tournament)
        return Response({"message": "Matches generated successfully."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_match_result_view(request, pk):
    match = get_object_or_404(Match, pk=pk)
    winner_id = request.data.get("winner_id")
    if not winner_id:
        return Response({"error": "Winner ID not provided."}, status=400)
    try:
        match.confirm_result(winner_id)
        return Response({"message": "Match result confirmed."})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def private_media_view(request, path):
    """
    This view serves private media files. It requires authentication and
    checks if the user is a participant in the match to which the file
    belongs.
    """
    try:
        match = Match.objects.get(result_proof=f"private_result_proofs/{path}")
    except Match.DoesNotExist:
        raise Http404

    is_participant = False
    if match.match_type == "individual":
        if request.user in [match.participant1_user, match.participant2_user]:
            is_participant = True
    else:
        if request.user in [
            match.participant1_team.captain,
            match.participant2_team.captain,
        ] or request.user in match.participant1_team.members.all() or request.user in match.participant2_team.members.all():
            is_participant = True

    if is_participant or request.user.is_staff:
        file_path = f"{settings.PRIVATE_MEDIA_ROOT}/{path}"
        return FileResponse(open(file_path, "rb"))
    else:
        return Response(
            {"error": "You do not have permission to access this file."}, status=403
        )
