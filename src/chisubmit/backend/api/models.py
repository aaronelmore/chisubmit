from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from enum import Enum

class CourseRoles(Enum):
    ADMIN = 0
    INSTRUCTOR = 1
    GRADER = 2
    STUDENT = 3

GradersAndStudents = set([CourseRoles.GRADER, CourseRoles.STUDENT])
AllExceptAdmin = set([CourseRoles.INSTRUCTOR, CourseRoles.GRADER, CourseRoles.STUDENT])
Students = set([CourseRoles.STUDENT])

class Course(models.Model):
    shortname = models.SlugField(unique = True)
    name = models.CharField(max_length=64)
    
    instructors = models.ManyToManyField(User, through='Instructor', related_name="instructor_in")
    graders = models.ManyToManyField(User, through='Grader', related_name="grader_in")
    students = models.ManyToManyField(User, through='Student', related_name="student_in")
    
    def __unicode__(self):
        return u"%s: %s" % (self.shortname, self.name)
    
    def has_instructor(self, user):
        return self.instructors.filter(username=user.username).exists()

    def has_grader(self, user):
        return self.graders.filter(username=user.username).exists()

    def has_student(self, user):
        return self.students.filter(username=user.username).exists()

    def has_user(self, user):
        return self.has_student(user) or self.has_instructor(user) or self.has_grader(user) 
    
    def has_access(self, user):
        return user.is_staff or user.is_superuser or self.has_user(user)
    
    def get_roles(self, user):
        roles = set()
        if self.has_instructor(user):
            roles.add(CourseRoles.INSTRUCTOR)
        if self.has_grader(user):
            roles.add(CourseRoles.GRADER)
        if self.has_student(user):
            roles.add(CourseRoles.STUDENT)
        if user.is_staff or user.is_superuser:
            roles.add(CourseRoles.ADMIN)
        return roles
    
    # OPTIONS
    GIT_USERNAME_USER = 'user-id'
    GIT_USERNAME_CUSTOM = 'custom'
    GIT_USERNAME_CHOICES = (
        (GIT_USERNAME_USER, 'Same as user id'),
        (GIT_USERNAME_CUSTOM, 'Custom git username'),
    )
    
    EXT_PER_TEAM = "per-team"
    EXT_PER_STUDENT = "per-student"
    EXT_CHOICES = (
        (EXT_PER_TEAM, 'Extensions per team'),
        (EXT_PER_STUDENT, 'Extensions per student'),
    )
    
    git_usernames = models.CharField(max_length=16, choices=GIT_USERNAME_CHOICES, default=GIT_USERNAME_USER)
    git_staging_usernames = models.CharField(max_length=16, choices=GIT_USERNAME_CHOICES, default=GIT_USERNAME_USER)
    extension_policy = models.CharField(max_length=16, choices=EXT_CHOICES, default=EXT_PER_STUDENT)
    default_extensions = models.IntegerField(default=0, validators = [MinValueValidator(0)])    
    
class Instructor(models.Model):
    user = models.ForeignKey(User)
    course = models.ForeignKey(Course)
    
    git_username = models.CharField(max_length=64)
    git_staging_username = models.CharField(max_length=64)

    def __unicode__(self):
        return u"Instructor %s of %s" % (self.user.username, self.course.shortname) 

    class Meta:
        unique_together = ("user", "course")

class Grader(models.Model):
    user = models.ForeignKey(User)
    course = models.ForeignKey(Course)
    
    git_username = models.CharField(max_length=64)
    git_staging_username = models.CharField(max_length=64)
    
    conflicts = models.ManyToManyField("Student", blank=True)
    
    def __unicode__(self):
        return u"Grader %s of %s" % (self.user.username, self.course.shortname)     
    
    class Meta:
        unique_together = ("user", "course")    
    
class Student(models.Model):
    user = models.ForeignKey(User)
    course = models.ForeignKey(Course)
    
    git_username = models.CharField(max_length=64)
    
    extensions = models.IntegerField(default=0, validators = [MinValueValidator(0)])
    dropped = models.BooleanField(default = False)
    
    def __unicode__(self):
        return u"Student %s of %s" % (self.user.username, self.course.shortname)     
    
    class Meta:
        unique_together = ("user", "course")    

class Assignment(models.Model):
    course = models.ForeignKey(Course)
    shortname = models.SlugField(unique = True)
    name = models.CharField(max_length=64)
    deadline = models.DateTimeField()

    # Options
    min_students = models.IntegerField(default=1, validators = [MinValueValidator(1)])
    max_students = models.IntegerField(default=1, validators = [MinValueValidator(1)])
    
    def __unicode__(self):
        return u"Assignment %s of %s" % (self.shortname, self.course.shortname)     

class RubricComponent(models.Model):    
    assignment = models.ForeignKey(Assignment)
    order = models.IntegerField(default=0, validators = [MinValueValidator(0)])
    description = models.CharField(max_length=64)
    points = models.DecimalField(max_digits=5, decimal_places=2)
    
    class Meta:
        unique_together = ("assignment", "description")
        ordering = ("assignment", "order")
        
        
class Team(models.Model):
    course = models.ForeignKey(Course)
    name = models.CharField(max_length=128)
    extensions = models.IntegerField(default=0, validators = [MinValueValidator(0)])
    active = models.BooleanField(default = True)
    
    registrations = models.ManyToManyField(Assignment, through='Registration') 
    
    class Meta:
        unique_together = ("course", "name")
        
        
class Registration(models.Model):
    team = models.ForeignKey(Team)
    assignment = models.ForeignKey(Assignment)

    grader = models.ForeignKey(Grader, null=True)
    final_submission = models.ForeignKey("Submission", related_name="final_submission_of", null=True) 

    class Meta:
        unique_together = ("team", "assignment")

class Submission(models.Model):
    registration = models.ForeignKey(Registration) 
    extensions_used = models.IntegerField(default=0, validators = [MinValueValidator(0)])
    commit_sha = models.CharField(max_length=40)
    submitted_at = models.DateTimeField()
        
class Grade(models.Model):
    team = models.ForeignKey(Team)
    rubric_component = models.ForeignKey(RubricComponent)
    
    points = models.DecimalField(max_digits=5, decimal_places=2)
    