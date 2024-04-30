from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .models import (
    Task,
    Team,
    Player,
    PlayerTask,
    League, 
    Meme,
    MemePlayer)

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.db import transaction
from datetime import datetime, date, timedelta
import pytz
import time
from typing import Callable

# Create your views here.
HOUR = 3600
ENERGY_MULTIPLIER = 1000
FULL_ENERGY: Callable[[Player], int] = lambda player: player.energy_limit_level*ENERGY_MULTIPLIER
MAX_BOOSTS_COUNT = 3
UPGRADE_PRICES = [
        10000, 
        20000, 
        40000, 
        80000, 
        160000, 
        320000, 
        640000, 
        1280000, 
        2560000, 
        5120000, 
        10240000, 
        20480000, 
        40960000, 
        81920000, 
        163840000]

class PlayerProcessor:
    @classmethod 
    def next_League_check(cls, player: Player) -> Player:
        try:
            next_league = LeagueProcessor.get_next_league(player.league.level)
        except:
            return player
        if next_league:
            if player.total_coins_earned >= player.league.coin_limit:
                player.league = next_league
        return player

    @classmethod
    def update_coins(cls, player: Player, new_coins_count) -> Player:
        player.coins_balance = new_coins_count
        cls.next_League_check(player)
        return player

    @classmethod
    def add_coins(cls, player: Player, coins_to_add: int) -> Player:
        player.coins_balance += coins_to_add
        cls.next_League_check(player)
        return player
    
    @classmethod
    def calculate_passive_income(cls, player: Player, passive_income_per_hour):
        current_time = int(time.time())
        total_seconds_offline = current_time - player.last_seen
        capped_seconds_offline = min(total_seconds_offline, 10800)
        passive_income = (capped_seconds_offline / HOUR) * passive_income_per_hour

        return int(passive_income)

    @classmethod
    def calculate_energy(cls, player: Player):
        current_time = int(time.time())
        total_seconds_offline = current_time - player.last_seen
        energy_balance = player.recharging_speed_level * total_seconds_offline
        player.energy_balance += int(energy_balance)
        if player.energy_balance > FULL_ENERGY(player):
            player.energy_balance = FULL_ENERGY(player)
        return player

    @classmethod
    def __use_rocket(cls, player: Player):
        rocket_count = player.rocket_count
        success = False
        if rocket_count > 0:
            success = True
            player.rocket_count = rocket_count - 1
        return player, rocket_count - 1, success
    
    @classmethod
    def __use_full_energy(cls, player: Player):
        full_energy_count = player.full_energy_count
        success = False
        if full_energy_count > 0:
            success = True
            player.full_energy_count = full_energy_count - 1
            player.energy_balance = FULL_ENERGY(player)
        return player, full_energy_count - 1, success

    @classmethod
    def use_boost(cls, player: Player, boost_type: str):
        boosts = {"rocket" : cls.__use_rocket, "full_energy" : cls.__use_full_energy}
        player, new_boosts_count, success = boosts[boost_type](player)
        return player, new_boosts_count, success

    @classmethod
    def update_boosts(cls, player: Player, timezone_str='Etc/GMT-2'):
        timezone = pytz.timezone(timezone_str)
        timestamp_date = datetime.fromtimestamp(player.last_seen, timezone).date()
        today = datetime.now(timezone).date()
        if timestamp_date < today:
            player.rocket_count = MAX_BOOSTS_COUNT
            player.full_energy_count = MAX_BOOSTS_COUNT
        return player
    
    @classmethod
    def calculate_passive_income(cls, player: Player):
        current_time = int(time.time())
        total_seconds_offline = current_time - player.last_seen
        passive_income = (total_seconds_offline / 3600) * player.total_coins_per_hour
        return int(passive_income)
    
class LeagueProcessor:
    @classmethod
    def get_next_league(cls, current_level: int):
        league = League.objects.filter(level = (current_level+1)).first()
        if league:
            return league
        return None

def initialize_user(request):
    telegram_id = request.GET.get("user_id")

    player = Player.objects.get(telegram_id=telegram_id)
    passive_income = PlayerProcessor.calculate_passive_income(player)
    player = PlayerProcessor.add_coins(player, passive_income)
    player = PlayerProcessor.calculate_energy(player)
    player = PlayerProcessor.update_boosts(player)
    player.last_seen = int(time.time())
    player.save()

    res = {
        "name": player.name,
        "league": player.league.name,
        "coins_count": player.coins_balance,
        "energy_count": player.energy_balance,
        "total_coins_earned": player.total_coins_earned,
        "coins_per_hour": player.total_coins_per_hour,
        "passive_income": passive_income
    }
    if player.team:
        res["team"] = {"id":player.team.id, "name":player.team.name, "logo":player.team.logo, "total":player.team.coins_count}

    return JsonResponse(res)

def get_player_energy(request):
    telegram_id = request.GET.get("user_id")
    player = Player.objects.get(telegram_id=telegram_id)
    player = PlayerProcessor.calculate_energy(player)
    player.last_seen = int(time.time())
    player.save()

    res = {
        "energy_count": player.energy_balance
    }

    return JsonResponse(res)

def get_task(request):
    task_id = request.GET.get("task_id")
    task = Task.objects.get(id=task_id)
    res = {
        "name": task.name,
        "description": task.description,
        "logo": "",
        "coins_reward": task.coins_reward,
        "penalty": task.penalty,
        "link": task.link,
    }
    return JsonResponse(res)


@csrf_exempt
def complete_task(request):
    player_task_id = request.POST.get("task_id")
    try:
        player_task = PlayerTask.objects.get(id=player_task_id)
        player_task.status = "CM"
        player_task.completion_date = timezone.now()
        player_task.save()
        player = player_task.player 
        player.coins_balance += player_task.task.coins_reward
        player.save()
        return JsonResponse({"status": "success"})
    except ObjectDoesNotExist:
        return JsonResponse(
            {"status": "Error. Task or Player does not exist."}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"status": f"Error. An error occurred: {str(e)}"}, status=500
        )


@csrf_exempt
def update_coins_and_energy(request):
    user_id = request.POST.get("user_id")
    coins_count = int(request.POST.get("coins_count"))
    energy_count = int(request.POST.get("energy_count"))
    player = Player.objects.get(telegram_id=user_id)
    player = PlayerProcessor.update_coins(player, coins_count)
    player.energy_balance = energy_count
    player.last_seen = int(time.time())
    player.save()
    return JsonResponse({"status": "success"})


def friends_reffered_count(request):
    user_id = request.GET.get("user_id")
    player = Player.objects.get(telegram_id=user_id)
    return JsonResponse({"friends_reffered_count": player.friends.count()})


def friends_list(request):
    user_id = request.GET.get("user_id")
    player = Player.objects.get(telegram_id=user_id)
    friends = player.friends.values("name", "telegram_id")
    return JsonResponse({"friends": list(friends)})


def get_user_tasks(request):
    user_id = request.GET.get("user_id")
    player = Player.objects.get(telegram_id=user_id)
    player_task_count = PlayerTask.objects.filter(player=player).count()
    total_tasks_count = Task.objects.filter(active=True).count()
    if player_task_count < total_tasks_count:
        existing_tasks = PlayerTask.objects.filter(player=player).values_list(
            "task", flat=True
        )
        missing_tasks = Task.objects.filter(active=True).exclude(id__in=existing_tasks)

        for task in missing_tasks:
            PlayerTask.objects.create(player=player, task=task)

    player_tasks = PlayerTask.objects.filter(player=player)
    tasks_data = list(
        player_tasks.values(
            "id",
            "task__name",
            "task__coins_reward",
            "task__description",
            "task__penalty",
            "task__link",
            "task__logo",
            "status",
        )
    )
    return JsonResponse({"tasks": tasks_data})

def get_user_boosts(request):
    user_id = request.GET.get("user_id")
    player = Player.objects.get(telegram_id=user_id)
    res = {
        "rocket": player.rocket_count,
        "full_energy": player.full_energy_count,
    }
    return JsonResponse(res)


def get_user_upgrades(request):
    user_id = request.GET.get("user_id")
    player = Player.objects.get(telegram_id=user_id)
    res = {
        "multitap_level": player.multitap_level,
        "recharging_speed_level": player.recharging_speed_level,
        "energy_limit_level": player.energy_limit_level,
    }
    return JsonResponse(res)


@csrf_exempt
def use_boost(request):
    user_id = request.POST.get("user_id")
    boost: str = request.POST.get("boost")
    try:
        player = Player.objects.get(telegram_id=user_id)
        response = {"boost": boost}
        player, count, success = PlayerProcessor.use_boost(player, boost)
        player.save()
        if not success:
            HttpResponse("Not enough boosts", status=406)
        else:
            response["count"] = count

        return JsonResponse(response)
    except Player.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Player not found."}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"An error occurred: {str(e)}"}, status=500
        )


@csrf_exempt
def buy_upgrade(request):
    user_id = request.POST.get("user_id")
    upgrade_request = request.POST.get("upgrade")
    upgrade = {
        "multitap": "multitap_level",
        "rechargingSpeed": "recharging_speed_level",
        "energyLimit": "energy_limit_level"
    }.get(upgrade_request)
    try:
        player = Player.objects.get(telegram_id=user_id)
        current_level = getattr(player, upgrade)
        try:
            cost = UPGRADE_PRICES[current_level-1]
        except IndexError:
            return JsonResponse(
                {
                    "status": "failed",
                    "message": "Maximum level reached.",
                },
                status=400,
            )

        if cost is None:
            return JsonResponse(
                {
                    "status": "failed",
                    "message": "Invalid upgrade request or maximum level reached.",
                },
                status=400,
            )
        if player.coins_balance < cost:
            return JsonResponse(
                {"status": "failed", "message": "Not enough coins."}, status=400
            )

        setattr(player, upgrade, current_level + 1)
        player.coins_balance -= cost
        player.save()
        return JsonResponse(
            {
                "status": "success",
                "message": f"{upgrade} upgraded to level {current_level + 1}.",
            }
        )
    except Player.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Player not found."}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"An error occurred: {str(e)}"}, status=500
        )


def get_teams(request):
    search_query = request.GET.get("search_query")
    teams = Team.objects.filter(name__startswith=search_query)
    teams_data = list(teams.values("id", "name"))
    return JsonResponse({"teams": teams_data})


def get_team(request):
    team_id = request.GET.get("team_id")
    team = Team.objects.get(id=team_id)
    res = {"name": team.name, "channel_link": team.channel_link}
    return JsonResponse(res)


@csrf_exempt
def join_team(request):
    user_id = request.POST.get("user_id")
    team_id = request.POST.get("team_id")

    try:
        player = Player.objects.get(telegram_id=user_id)
        team = Team.objects.get(id=team_id)
        player.team = team
        player.save()
        return JsonResponse(
            {"status": "success", "message": "Successfully joined the team."}
        )
    except Player.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Player not found."}, status=404
        )
    except Team.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Team not found."}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"An error occurred: {str(e)}"}, status=500
        )


@csrf_exempt
def leave_team(request):
    user_id = request.POST.get("user_id")

    try:
        player = Player.objects.get(telegram_id=user_id)
        player.team = None
        player.save()
        return JsonResponse(
            {"status": "success", "message": "Successfully left the team."}
        )
    except Player.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Player not found."}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"An error occurred: {str(e)}"}, status=500
        )


def get_top_teams(request):
    limit = request.GET.get("limit")
    if not limit: limit = 5
    top_teams = Team.objects.annotate(
        total_coins_earned=Sum("users__total_coins_earned")
    ).order_by("-total_coins_earned")[:limit]
    teams_data = list(top_teams.values("id", "name"))
    return JsonResponse({"teams": teams_data})

def get_league(request):
    time_period = request.GET.get("time_period")
    league = request.GET.get("league")
    players = Player.objects.filter(league=league).order_by(
        "total_earned_day" if time_period == "day" else "total_earned_week"
    )
    players_league_data = list(
        players.values(
            "telegram_id",
            "name",
            "total_earned_day" if time_period == "day" else "total_earned_week",
        )
    )
    return JsonResponse({"league": players_league_data})

def get_all_leagues(request):
    leagues = list(League.objects.values().all())
    return JsonResponse(
        {
            "leagues": leagues
        }
    )


def get_player_memes(request):
    user_id = request.GET.get("user_id")
    try:
        player = Player.objects.get(pk=user_id)
    except Player.DoesNotExist:
        return JsonResponse({"error": "Player not found"}, status=404)

    memes_data = []
    all_memes = Meme.objects.all()

    for meme in all_memes:
        try:
            player_meme = MemePlayer.objects.get(player=player, meme=meme)
            memes_data.append(
                {
                    "meme_id": meme.id,
                    "name": meme.name,
                    "level": player_meme.current_level,
                    "coins_per_hour": player_meme.current_coins_per_hour,
                    "upgrade_cost": player_meme.current_upgrade_cost,
                    "logo": player_meme.meme.logo,
                }
            )
        except MemePlayer.DoesNotExist:
            memes_data.append(
                {
                    "meme_id": meme.id,
                    "name": meme.name,
                    "level": 1,
                    "coins_per_hour": meme.coins_per_hour,
                    "upgrade_cost": meme.upgrade_price,
                    "logo": meme.logo,
                }
            )
    return JsonResponse({"memes": memes_data})

@csrf_exempt
def manage_meme(request):
    player_id = request.POST.get("user_id")
    meme_id = request.POST.get("meme_id")

    # Try to fetch player and meme details
    try:
        player = Player.objects.get(pk=player_id)
        meme = Meme.objects.get(pk=meme_id)
    except (Player.DoesNotExist, Meme.DoesNotExist):
        return JsonResponse({"error": "Player or Meme not found"}, status=404)

    # Determine if the meme is already owned by the player
    meme_owned = MemePlayer.objects.filter(player=player, meme=meme).exists()

    if not meme_owned:
        # Handle purchase
        if player.coins_balance < meme.upgrade_price:
            return JsonResponse({"error": "Insufficient funds"}, status=400)

        # Deduct the cost and update player balance
        player.coins_balance -= meme.upgrade_price
        player.save()

        # Create a new ownership record
        new_meme_player = MemePlayer(
            player=player,
            meme=meme,
            current_coins_per_hour=meme.coins_per_hour,
            current_upgrade_cost=meme.upgrade_price,
        )
        new_meme_player.save()

        memesplayer = MemePlayer.objects.filter(player=player).all()
        coins_per_hour = 0
        for pair in memesplayer:
            coins_per_hour += pair.current_coins_per_hour
        player.total_coins_per_hour = coins_per_hour
        player.save()

        # Return success response
        return JsonResponse(
            {
                "message": "Meme purchased successfully",
                "player_coins_balance": player.coins_balance,
                "coins_per_hour": player.total_coins_per_hour,
                "meme_details": {
                    "name": meme.name,
                    "coins_per_hour": new_meme_player.coins_per_hour,
                    "upgrade_cost": new_meme_player.upgrade_cost,
                },
            }
        )
    else:
        # Handle upgrade
        memeplayer = MemePlayer.objects.get(player=player, meme=meme)
        next_level = memeplayer.current_level + 1
        new_upgrade_cost = memeplayer.meme.upgrade_price * (2**next_level)

        if player.coins_balance < new_upgrade_cost:
            return JsonResponse({"error": "Insufficient funds"}, status=400)

        # Update memeplayer details
        memeplayer.current_level = next_level
        memeplayer.current_coins_per_hour = int(
            memeplayer.meme.coins_per_hour * (1.1**next_level)
        )
        memeplayer.current_upgrade_cost = new_upgrade_cost
        memeplayer.save()

        # Deduct the cost and update player balance
        player.coins_balance -= new_upgrade_cost
        memesplayer = MemePlayer.objects.filter(player=player).all()
        coins_per_hour = 0
        for pair in memesplayer:
            coins_per_hour += pair.current_coins_per_hour
        player.total_coins_per_hour = coins_per_hour
        player.save()
        

        # Return success response
        return JsonResponse(
            {
                "message": "Meme upgraded successfully",
                "new_level": memeplayer.current_level,
                "new_coins_per_hour": memeplayer.current_coins_per_hour,
                "new_upgrade_cost": memeplayer.current_upgrade_cost,
                "player_coins_balance": player.coins_balance,
                "coins_per_hour": player.total_coins_per_hour
            }
        )



def get_memeplayer(request):
    # Assumes that 'memeplayer_id' is passed as a parameter in the GET request
    memeplayer_id = request.GET.get("memeplayer_id")
    try:
        memeplayer = MemePlayer.objects.get(pk=memeplayer_id)
        response_data = {
            "memeplayer_id": memeplayer.pk,
            "player_id": memeplayer.player.pk,
            "meme_id": memeplayer.meme.pk,
            "purchase_time": memeplayer.purchase_time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": memeplayer.current_level,
            "coins_per_hour": memeplayer.current_coins_per_hour,
            "upgrade_cost": memeplayer.current_upgrade_cost,
        }
        return JsonResponse(response_data)
    except MemePlayer.DoesNotExist:
        return JsonResponse({"error": "MemePlayer not found"}, status=404)