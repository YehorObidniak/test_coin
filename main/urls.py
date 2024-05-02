from django.urls import path
from .views import (
    initialize_user,
    get_task,
    complete_task,
    update_coins_and_energy,
    friends_reffered_count,
    friends_list,
    get_user_tasks,
    get_user_boosts,
    get_user_upgrades,
    use_boost,
    buy_upgrade,
    get_teams,
    get_team,
    join_team,
    leave_team,
    get_top_teams,
    get_all_leagues,
    get_player_memes,
    get_player_energy,
    manage_meme,
    send_invite_message
)

urlpatterns = [
    path('initialize_user/', initialize_user, name='initialize_user'),
    path('get_task/', get_task, name='get_task'),
    path('complete_task/', complete_task, name='complete_task'),
    path('update_coins_and_energy/', update_coins_and_energy, name='update_coins_and_energy'),
    path('friends_reffered_count/', friends_reffered_count, name='friends_reffered_count'),
    path('friends_list/', friends_list, name='friends_list'),
    path('get_user_tasks/', get_user_tasks, name='get_user_tasks'),
    path('get_user_boosts/', get_user_boosts, name='get_user_boosts'),
    path('get_user_upgrades/', get_user_upgrades, name='get_user_upgrades'),
    path('use_boost/', use_boost, name='use_boost'),
    path('buy_upgrade/', buy_upgrade, name='buy_upgrade'),
    path('get_teams/', get_teams, name='get_teams'),
    path('get_team/', get_team, name='get_team'),
    path('join_team/', join_team, name='join_team'),
    path('leave_team/', leave_team, name='leave_team'),
    path('get_top5_teams/', get_top_teams, name='get_top5_teams'),
    path('get_all_leagues/', get_all_leagues, name='get_all_leagues'),
    path('get_player_memes', get_player_memes, name='get_player_memes'),
    path('get_player_energy', get_player_energy, name='get_player_energy'),
    path('manage_meme/', manage_meme, name='manage_meme'),
    path('send_invite_message/', send_invite_message, name='send_invite')
    # path()
]