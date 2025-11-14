from users.models import User

from .models import Team, TeamInvitation, TeamMembership


class ApplicationError(Exception):
    pass


def invite_member_service(team: Team, from_user: User, to_user_id: int):
    """
    Invites a user to a team.
    """
    if from_user != team.captain:
        raise ApplicationError("Only the team captain can invite members.")

    try:
        to_user = User.objects.get(id=to_user_id)
    except User.DoesNotExist:
        raise ApplicationError("User not found.")

    if to_user in team.members.all():
        raise ApplicationError("User is already a member of the team.")

    invitation, created = TeamInvitation.objects.get_or_create(
        from_user=from_user, to_user=to_user, team=team
    )
    if not created:
        raise ApplicationError("Invitation already sent.")

    return invitation


def respond_to_invitation_service(invitation_id: int, user: User, status: str):
    """
    Responds to a team invitation.
    """
    try:
        invitation = TeamInvitation.objects.get(id=invitation_id, to_user=user)
    except TeamInvitation.DoesNotExist:
        raise ApplicationError("Invitation not found.")

    if status == "accepted":
        invitation.status = "accepted"
        TeamMembership.objects.create(user=user, team=invitation.team)
        invitation.save()
    elif status == "rejected":
        invitation.status = "rejected"
        invitation.save()
    else:
        raise ApplicationError("Invalid status.")

    return invitation


def leave_team_service(team: Team, user: User):
    """
    Allows a user to leave a team.
    """
    if user not in team.members.all():
        raise ApplicationError("You are not a member of this team.")
    if user == team.captain:
        raise ApplicationError(
            "The captain cannot leave the team. Please transfer captaincy first."
        )

    team.members.remove(user)


def remove_member_service(team: Team, captain: User, member_id: int):
    """
    Allows a captain to remove a member from a team.
    """
    if captain != team.captain:
        raise ApplicationError("Only the team captain can remove members.")

    try:
        member = User.objects.get(id=member_id)
    except User.DoesNotExist:
        raise ApplicationError("User not found.")

    if member not in team.members.all():
        raise ApplicationError("User is not a member of the team.")

    if member == team.captain:
        raise ApplicationError("The captain cannot be removed from the team.")

    team.members.remove(member)
