from rest_framework import serializers
from chisubmit.backend.api.models import Course, GradersAndStudents, AllExceptAdmin,\
    Students, Student, Instructor, Grader, Team, Assignment, ReadWrite,\
    OwnerPermissions, Read, RubricComponent, TeamMember, Registration
from django.contrib.auth.models import User
from rest_framework.reverse import reverse
from rest_framework.relations import RelatedField
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy

class FieldPermissionsMixin(object):
    def get_filtered_data(self, course, user):
        data = dict(self.data)

        if hasattr(self, "hidden_fields"):
            roles = course.get_roles(user)
            fields = data.keys()
            for f in fields:
                if f in self.hidden_fields:
                    if roles.issubset(self.hidden_fields[f]):
                        data.pop(f)
        
        return data
        
    def filter_initial_data(self, course, user, is_owner=False, raise_exception=False):
        roles = course.get_roles(user)
        fields = self.initial_data.keys()
        owner_override = getattr(self, "owner_override", {})

        for f in fields:
            if hasattr(self, "hidden_fields") and f in self.hidden_fields:
                if not (is_owner and OwnerPermissions.READ in owner_override.get(f, [])):
                    if roles.issubset(self.hidden_fields[f]):
                        self.initial_data.pop(f)
            elif hasattr(self, "readonly_fields") and f in self.readonly_fields:
                if not (is_owner and OwnerPermissions.WRITE in owner_override.get(f, [])):
                    if roles.issubset(self.readonly_fields[f]):
                        self.initial_data.pop(f)                
        
class UserSerializer(serializers.Serializer, FieldPermissionsMixin):
    username = serializers.CharField(max_length=30)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()    
    
    readonly_fields = { "username": AllExceptAdmin,
                        "first_name": AllExceptAdmin,
                        "last_name": AllExceptAdmin,
                        "email": AllExceptAdmin
                      }    
    
    def create(self, validated_data):
        return User.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        return instance      
    

class CourseSerializer(serializers.Serializer, FieldPermissionsMixin):
    course_id = serializers.SlugField()
    name = serializers.CharField(max_length=64)
    
    url = serializers.SerializerMethodField()    
    instructors_url = serializers.SerializerMethodField()
    graders_url = serializers.SerializerMethodField()
    students_url = serializers.SerializerMethodField()
    assignments_url = serializers.SerializerMethodField()
    teams_url = serializers.SerializerMethodField()
    
    
    git_server_connstr = serializers.CharField(max_length=64, required=False)
    git_staging_connstr = serializers.CharField(max_length=64, required=False)
    git_usernames = serializers.ChoiceField(choices=Course.GIT_USERNAME_CHOICES, default=Course.GIT_USERNAME_USER)
    git_staging_usernames = serializers.ChoiceField(choices=Course.GIT_USERNAME_CHOICES, default=Course.GIT_USERNAME_USER)
    extension_policy = serializers.ChoiceField(choices=Course.EXT_CHOICES, default=Course.EXT_PER_STUDENT)
    default_extensions = serializers.IntegerField(default=0, min_value=0)    
    
    hidden_fields = { "git_staging_connstr": Students,    
                      "git_usernames": GradersAndStudents,
                      "git_staging_usernames": GradersAndStudents,
                      "extension_policy": GradersAndStudents,
                      "default_extensions": GradersAndStudents
                    }
    
    readonly_fields = { "course_id": AllExceptAdmin,
                        "name": AllExceptAdmin,
                        "git_server_connstr": AllExceptAdmin,
                        "git_staging_connstr": AllExceptAdmin,                        
                        "git_usernames": AllExceptAdmin,
                        "git_staging_usernames": AllExceptAdmin,
                        "extension_policy": AllExceptAdmin,
                        "default_extensions": AllExceptAdmin
                      }

    def get_url(self, obj):
        return reverse('course-detail', args=[obj.course_id], request=self.context["request"])

    def get_instructors_url(self, obj):
        return reverse('instructor-list', args=[obj.course_id], request=self.context["request"])    

    def get_graders_url(self, obj):
        return reverse('grader-list', args=[obj.course_id], request=self.context["request"])    
    
    def get_students_url(self, obj):
        return reverse('student-list', args=[obj.course_id], request=self.context["request"])    
    
    def get_assignments_url(self, obj):
        return reverse('assignment-list', args=[obj.course_id], request=self.context["request"])      

    def get_teams_url(self, obj):
        return reverse('team-list', args=[obj.course_id], request=self.context["request"])      
    
    def create(self, validated_data):
        return Course.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.course_id = validated_data.get('course_id', instance.course_id)
        instance.name = validated_data.get('name', instance.name)
        instance.git_server_connstr = validated_data.get('git_server_connstr', instance.git_server_connstr)
        instance.git_staging_connstr = validated_data.get('git_staging_connstr', instance.git_staging_connstr)
        instance.git_usernames = validated_data.get('git_usernames', instance.git_usernames)
        instance.git_staging_usernames = validated_data.get('git_staging_usernames', instance.git_staging_usernames)
        instance.extension_policy = validated_data.get('extension_policy', instance.extension_policy)
        instance.default_extensions = validated_data.get('default_extensions', instance.default_extensions)
        instance.save()
        return instance
    
    
class InstructorSerializer(serializers.Serializer, FieldPermissionsMixin):
    url = serializers.SerializerMethodField()
    username = serializers.SlugRelatedField(
        source="user",
        queryset=User.objects.all(),
        slug_field='username'
    )
    user = UserSerializer(read_only=True)
    git_username = serializers.CharField(max_length=64, required=False)
    git_staging_username = serializers.CharField(max_length=64, required=False)
    
    hidden_fields = { "git_username": AllExceptAdmin,
                      "git_staging_username": AllExceptAdmin }
    
    readonly_fields = { }
    
    owner_override = {"git_username": ReadWrite,
                      "git_staging_username": ReadWrite }
    
    def get_url(self, obj):
        return reverse('instructor-detail', args=[self.context["course"].course_id, obj.user.username], request=self.context["request"])
    
    def create(self, validated_data):
        return Instructor.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.git_username = validated_data.get('git_username', instance.git_username)
        instance.git_staging_username = validated_data.get('git_staging_username', instance.git_staging_username)
        instance.save()
        return instance    
    

class GraderSerializer(serializers.Serializer, FieldPermissionsMixin):
    url = serializers.SerializerMethodField()
    username = serializers.SlugRelatedField(
        source="user",
        queryset=User.objects.all(),
        slug_field='username'
    )
    user = UserSerializer(read_only=True)
    git_username = serializers.CharField(max_length=64, required=False)
    git_staging_username = serializers.CharField(max_length=64, required=False)
    
    hidden_fields = { "git_username": AllExceptAdmin,
                      "git_staging_username": AllExceptAdmin }
    
    readonly_fields = { }     
    
    owner_override = {"git_username": ReadWrite,
                      "git_staging_username": ReadWrite }    
    
    def get_url(self, obj):
        return reverse('grader-detail', args=[self.context["course"].course_id, obj.user.username], request=self.context["request"])
    
    def create(self, validated_data):
        return Grader.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.git_username = validated_data.get('git_username', instance.git_username)
        instance.git_staging_username = validated_data.get('git_staging_username', instance.git_staging_username)
        instance.save()
        return instance       
    
    
class StudentSerializer(serializers.Serializer, FieldPermissionsMixin):
    url = serializers.SerializerMethodField()
    username = serializers.SlugRelatedField(
        source="user",
        queryset=User.objects.all(),
        slug_field='username'
    )
    user = UserSerializer(read_only=True, required=False)
    git_username = serializers.CharField(max_length=64, required=False)
    
    extensions = serializers.IntegerField(default=0, min_value=0)
    dropped = serializers.BooleanField(default=False)
    
    hidden_fields = { "git_username": Students, 
                      "dropped": Students }
    
    readonly_fields = { "extensions": GradersAndStudents,
                        "dropped": GradersAndStudents
                      }     
    
    owner_override = { "git_username": ReadWrite }
        
    def get_url(self, obj):
        return reverse('student-detail', args=[self.context["course"].course_id, obj.user.username], request=self.context["request"])
    
    def create(self, validated_data):
        return Student.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.git_username = validated_data.get('git_username', instance.git_username)
        instance.extensions = validated_data.get('extensions', instance.extensions)
        instance.dropped = validated_data.get('dropped', instance.dropped)
        instance.save()
        return instance    
    
    
    
class AssignmentSerializer(serializers.Serializer, FieldPermissionsMixin):
    assignment_id = serializers.SlugField()
    name = serializers.CharField(max_length=64)
    deadline = serializers.DateTimeField()
    
    url = serializers.SerializerMethodField()
    rubric_url = serializers.SerializerMethodField()
    
    min_students = serializers.IntegerField(default=1, min_value=1)
    max_students = serializers.IntegerField(default=1, min_value=1)
    
    readonly_fields = { "assignment_id": GradersAndStudents,
                        "name": GradersAndStudents,
                        "deadline": GradersAndStudents,
                        "min_students": GradersAndStudents,
                        "max_students": GradersAndStudents
                      }       
    
    def get_url(self, obj):
        return reverse('assignment-detail', args=[self.context["course"].course_id, obj.assignment_id], request=self.context["request"])

    def get_rubric_url(self, obj):
        return reverse('rubric-list', args=[self.context["course"].course_id, obj.assignment_id], request=self.context["request"])
    
    def create(self, validated_data):
        return Assignment.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.assignment_id = validated_data.get('assignment_id', instance.assignment_id)
        instance.name = validated_data.get('name', instance.name)
        instance.deadline = validated_data.get('deadline', instance.deadline)
        instance.min_students = validated_data.get('min_students', instance.min_students)
        instance.max_students = validated_data.get('max_students', instance.max_students)
        instance.save()
        return instance    
  

class RubricComponentSerializer(serializers.Serializer, FieldPermissionsMixin):
    order = serializers.IntegerField(default=1, min_value=1)
    description = serializers.CharField(max_length=64)
    points = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    url = serializers.SerializerMethodField()   
    
    readonly_fields = { "order": GradersAndStudents,
                        "description": GradersAndStudents,
                        "points": GradersAndStudents
                      }       
    
    def get_url(self, obj):
        return reverse('rubric-detail', args=[self.context["course"].course_id, self.context["assignment"].assignment_id, obj.pk], request=self.context["request"])
    
    def create(self, validated_data):
        return RubricComponent.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.order = validated_data.get('order', instance.order)
        instance.description = validated_data.get('description', instance.description)
        instance.points = validated_data.get('points', instance.points)
        instance.save()
        return instance

    
class TeamSerializer(serializers.Serializer, FieldPermissionsMixin):
    name = serializers.SlugField()
    extensions = serializers.IntegerField(default=0, min_value=0)
    active = serializers.BooleanField(default = True)
        
    url = serializers.SerializerMethodField()
    students_url = serializers.SerializerMethodField()
    assignments_url = serializers.SerializerMethodField()

    hidden_fields = { "active": Students }       
        
    readonly_fields = { "name": GradersAndStudents,
                        "extensions": GradersAndStudents
                      }       
    
    def get_url(self, obj):
        return reverse('team-detail', args=[self.context["course"].course_id, obj.name], request=self.context["request"])

    def get_students_url(self, obj):
        return reverse('teammember-list', args=[self.context["course"].course_id, obj.name], request=self.context["request"])

    def get_assignments_url(self, obj):
        return reverse('registration-list', args=[self.context["course"].course_id, obj.name], request=self.context["request"])
    
    def create(self, validated_data):
        return Team.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.extensions = validated_data.get('extensions', instance.extensions)
        instance.active = validated_data.get('active', instance.min_students)
        instance.save()
        return instance         
    
class PersonRelatedField(RelatedField):
    default_error_messages = {
        'does_not_exist': ugettext_lazy('Object with username={value} does not exist.'),
        'invalid': ugettext_lazy('Invalid value.'),
    }
    
    def __init__(self, **kwargs):    
        super(PersonRelatedField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(user__username = data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', value=smart_text(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return obj.user.username

    
class TeamMemberSerializer(serializers.Serializer, FieldPermissionsMixin):    
    url = serializers.SerializerMethodField()
    username = PersonRelatedField(source = "student",
                                  queryset=Student.objects.all()
                                  )
    student = StudentSerializer(read_only=True)
    confirmed = serializers.BooleanField(default=False)
    
    readonly_fields = { "confirmed": GradersAndStudents }        

    def get_url(self, obj):
        return reverse('teammember-detail', args=[self.context["course"].course_id, obj.team.name, obj.student.user.username], request=self.context["request"])
    
    def create(self, validated_data):
        return TeamMember.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.confirmed = validated_data.get('confirmed', instance.confirmed)
        instance.save()
        return instance
    
class RegistrationSerializer(serializers.Serializer, FieldPermissionsMixin):    
    url = serializers.SerializerMethodField()
    assignment_id = serializers.SlugRelatedField(
        source="assignment",
        queryset=Assignment.objects.all(),
        slug_field='assignment_id'
    )
    assignment = AssignmentSerializer(read_only=True, required=False) 
    grader_username = PersonRelatedField(
                                         source = "grader",
                                         queryset=Grader.objects.all(),
                                         required = False
                                         )
    grader = GraderSerializer(read_only=True, required=False)
    #TODO: final_submission

    hidden_fields = { 
                      "grader_username": Students,
                      "grader": Students                      
                    }   

    def get_url(self, obj):
        return reverse('registration-detail', args=[self.context["course"].course_id, obj.team.name, obj.assignment.assignment_id], request=self.context["request"])
    
    def create(self, validated_data):
        return Registration.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        return instance            
    

class RegistrationRequestSerializer(serializers.Serializer):
    students = serializers.ListField(
                                      child = serializers.CharField()
                                      )
    
class RegistrationResponseSerializer(serializers.Serializer):
    new_team = serializers.BooleanField()
    team = TeamSerializer()
    team_members = serializers.ListField(
                                         child = TeamMemberSerializer()
                                         )
    registration = RegistrationSerializer()    