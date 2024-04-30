from django.contrib import admin
from django import forms
from .models import Player, Team, Task, PlayerTask, League, Meme, MemePlayer
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

class PlayerTaskInlineForTask(admin.TabularInline):
    model = PlayerTask
    extra = 0
    fields = ['player', 'status', 'completion_date']
    readonly_fields = ['completion_date']
    autocomplete_fields = ['player']

class PlayerTaskInlineForPlayer(admin.TabularInline):
    model = PlayerTask
    extra = 0
    fields = ['task', 'status', 'completion_date']
    readonly_fields = ['completion_date']

class PlayerInlineForm(forms.ModelForm):
    player = forms.ModelChoiceField(
        queryset=Player.objects.all(),
        widget=ForeignKeyRawIdWidget(Player._meta.get_field('team').remote_field, admin.site),
        required=False
    )

    class Meta:
        model = Player
        fields = '__all__'

class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0
    

class PlayerAdminForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(PlayerAdminForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['friends'].queryset = Player.objects.exclude(telegram_id=instance.telegram_id)

class PlayerAdmin(admin.ModelAdmin):
    form = PlayerAdminForm
    filter_horizontal = ('friends',)
    inlines = [PlayerTaskInlineForPlayer,]
    search_fields = ['name', 'telegram_id']
    


class TaskAdmin(admin.ModelAdmin):
    inlines = [PlayerTaskInlineForTask,]

class TeamAdmin(admin.ModelAdmin):
    inlines = [PlayerInline,]

class LeagueAdmin(admin.ModelAdmin):
    pass

class MemeAdmin(admin.ModelAdmin):
    pass

class MemePlayerAdmin(admin.ModelAdmin):
    pass

admin.site.register(Player, PlayerAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(PlayerTask)
admin.site.register(League, LeagueAdmin)
admin.site.register(Meme, MemeAdmin)
admin.site.register(MemePlayer, MemePlayerAdmin)