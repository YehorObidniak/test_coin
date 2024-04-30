from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import time

def CURRENT_TIME(): int(time.time())

class Team(models.Model):
    name = models.CharField(max_length=100)
    coins_count = models.IntegerField(default=0)
    channel_link = models.CharField(max_length=100, default="")
    logo = models.CharField(max_length=1023, null=True, blank=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    telegram_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    league = models.ForeignKey("League", on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey("Team", on_delete=models.SET_NULL, null=True, blank=True, related_name="users")
    friends = models.ManyToManyField("self", blank=True, symmetrical=True)
    referred_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    level_validators = [MinValueValidator(1), MaxValueValidator(100)]
    multitap_level = models.IntegerField(validators=level_validators, default=1)
    recharging_speed_level = models.IntegerField(validators=level_validators, default=1)
    energy_limit_level = models.IntegerField(validators=level_validators, default=1)
    rocket_count = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(3)], default=3)
    full_energy_count = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(1)], default=1)
    energy_balance = models.IntegerField(validators=[MinValueValidator(0)], default=1000)
    coins_balance = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_coins_earned = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    last_seen = models.BigIntegerField(default=CURRENT_TIME, blank=True)
    total_earned_day = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_earned_week = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    total_coins_per_hour = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):
        if not self._state.adding:
            db_instance = Player.objects.get(pk=self.pk)
            if self.coins_balance > db_instance.coins_balance:
                difference = self.coins_balance - db_instance.coins_balance
                self.total_coins_earned += difference
        super().save(*args, **kwargs)
        if self.friends.filter(pk=self.pk).exists():
            self.friends.remove(self)


class League(models.Model):
    name = models.CharField(max_length=31, unique=True)
    level = models.IntegerField(default=1, unique=True, null=False)
    coin_limit = models.BigIntegerField(validators=[MinValueValidator(0)], null=False)
    logo = models.CharField(max_length=1023, null=True, blank=True)


class Task(models.Model):
    name = models.CharField(max_length=100)  #
    coins_reward = models.IntegerField(default=10000)  #
    logo = models.CharField(max_length=255, default="")#
    description = models.CharField(max_length=255)  #
    penalty = models.CharField(max_length=255, blank=True)  #
    link = models.CharField(max_length=255)
    players = models.ManyToManyField(Player, through="PlayerTask", related_name="tasks")
    active = models.BooleanField(default=True)


class PlayerTask(models.Model):
    STATUS_CHOICES = [
        ("AV", "Available"),
        ("CM", "Completed"),
        ("PE", "Pending"),
        ("RE", "Rejected"),
    ]
    
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    status = models.CharField(max_length=9, choices=STATUS_CHOICES, default="AV")
    completion_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("player", "task")
    
class Meme(models.Model):
    name = models.CharField(max_length=255, null=False)
    data = models.JSONField()
    coins_per_hour = models.IntegerField(null=False)
    upgrade_price = models.IntegerField(null=False)
    logo = models.CharField(max_length=1023)


class MemePlayer(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE)
    purchase_time = models.DateTimeField(auto_now_add=True)
    current_level = models.IntegerField(default=1)
    current_coins_per_hour = models.IntegerField(default=1)
    current_upgrade_cost = models.IntegerField(default=1)

    class Meta:
        unique_together = ("player", "meme")