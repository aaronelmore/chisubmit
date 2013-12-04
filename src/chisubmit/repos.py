from github import Github, InputGitAuthor
from github.GithubException import GithubException

import pytz
from datetime import datetime

from chisubmit import ChisubmitException

class GithubConnection(object):
    def __init__(self, access_token, organization):
        self.gh = Github(access_token)

        try:
            self.organization = self.gh.get_organization(organization)
        except GithubException as ge:
            if ge.status == 401:
                raise ChisubmitException("Invalid Github Credentials")
            elif ge.status == 404:
                raise ChisubmitException("Organization %s does not exist" % organization)            
            else:
                raise ChisubmitException("Unexpected error accessing organization %s (%i: %s)" % (organization, ge.status, ge.data["message"]))            

    def create_team_repository(self, course, team, private=True):
        repo_name = "%s-%s" % (course.id, team.id)
        team_name = repo_name
        student_names = ", ".join(["%s %s" % (s.first_name, s.last_name) for s in team.students])
        repo_description = "%s: Team %s (%s)" % (course.name, team.id, student_names)
        github_instructors = self.__get_team_by_name(course.github_instructors_team)
        
        try:
            github_repo = self.organization.create_repo(repo_name, description=repo_description, private=private)
        except GithubException as ge:
            raise ChisubmitException("Unexpected exception creating repository %s (%i: %s)" % (repo_name, ge.status, ge.data["message"]))
        
        try:
            github_instructors.add_to_repos(github_repo)
        except GithubException as ge:
            raise ChisubmitException("Unexpected exception adding repository to Instructors team (%i: %s)" % (ge.status, ge.data["message"]))
        
        team.github_repo = repo_name
        
        try:
            github_team = self.organization.create_team(team_name, [github_repo], "push")
        except GithubException as ge:
            raise ChisubmitException("Unexpected exception creating team %s (%i: %s)" % (team_name, ge.status, ge.data["message"]))

        team.github_team = team_name

        for s in team.students:
            github_student = self.__get_user(s.github_id)
            try:
                github_team.add_to_members(github_student)
            except GithubException as ge:
                raise ChisubmitException("Unexpected exception adding user %s to team (%i: %s)" % (s.github_id, ge.status, ge.data["message"]))

    def update_team_repository(self, team):
        github_team = self.__get_team_by_name(team.github_team)

        for s in team.students:
            github_student = self.__get_user(s.github_id)
            try:
                github_team.add_to_members(github_student)
            except GithubException as ge:
                raise ChisubmitException("Unexpected exception adding user %s to team (%i: %s)" % (s.github_id, ge.status, ge.data["message"]))

    def create_submission_tag(self, team, tag_name, tag_message, commit_sha):
        github_repo = self.organization.get_repo(team.github_repo)
        
        commit = self.get_commit(team, commit_sha)
        
        this_user = self.gh.get_user()
        tz = pytz.timezone("America/Chicago")
        dt = tz.localize(datetime.now())
        iu = InputGitAuthor(this_user.name, this_user.email, dt.isoformat())
        
        tag = github_repo.create_git_tag(tag_name, tag_message, commit.sha, "commit", iu)
        ref = github_repo.create_git_ref("refs/tags/" + tag.tag, tag.sha)
        
    def update_submission_tag(self, team, tag_name, tag_message, commit_sha):
        submission_tag_ref = self.get_submission_tag_ref(team, tag_name)
        submission_tag_ref.delete()
        
        self.create_submission_tag(team, tag_name, tag_message, commit_sha)
        
    def get_submission_tag_ref(self, team, tag_name):
        github_repo = self.organization.get_repo(team.github_repo)
        
        try:
            submission_tag_ref = github_repo.get_git_ref("tags/" + tag_name)
        except GithubException as ge:
            if ge.status == 404:
                return None
            else:
                raise ChisubmitException("Unexpected error when fetching tag %s (%i: %s)" % (tag_name, ge.status, ge.data["message"]))            
        
        return submission_tag_ref

            
    def get_submission_tag(self, team, tag_name):
        github_repo = self.organization.get_repo(team.github_repo)
        
        submission_tag_ref = self.get_submission_tag_ref(team, tag_name)
        
        if submission_tag_ref is None:
            return None
                
        submission_tag = github_repo.get_git_tag(submission_tag_ref.object.sha)
        
        return submission_tag  

    def delete_team_repository(self, team):
        try:
            github_repo = self.organization.get_repo(team.github_repo)
        except GithubException as ge:
            raise ChisubmitException("Unexpected exception fetching repository %s (%i: %s)" % (team.github_repo, ge.status, ge.data["message"]))
        
        try:
            github_repo.delete()
        except GithubException as ge:
            raise ChisubmitException("Unexpected exception deleting repository %s (%i: %s)" % (team.github_repo, ge.status, ge.data["message"]))
        
        team.github_repo = None
        
        github_team = self.__get_team_by_name(team.github_team)

        try:
            github_team.delete()
        except GithubException as ge:
            raise ChisubmitException("Unexpected exception deleting team %s (%i: %s)" % (team.github_team, ge.status, ge.data["message"]))

        team.github_team = None

    def get_commit(self, team, commit_sha):
        try:
            github_repo = self.organization.get_repo(team.github_repo)
            commit = github_repo.get_commit(commit_sha)
            return commit
        except GithubException as ge:
            if ge.status == 404:
                return None
            else:
                raise ChisubmitException("Unexpected error when fetching commit %s (%i: %s)" % (commit_sha, ge.status, ge.data["message"]))            


    def __get_user(self, username):
        try:
            user = self.gh.get_user(username)
            return user
        except GithubException as ge:
            if ge.status == 404:
                return None
            else:
                raise ChisubmitException("Unexpected error with user %s (%i: %s)" % (username, ge.status, ge.data["message"]))            

    def __get_team_by_name(self, team_name):
        try:
            teams = self.organization.get_teams()
            for t in teams:
                if t.name == team_name:
                    return t
            return None
        except GithubException as ge:
            raise ChisubmitException("Unexpected error with team %s (%i: %s)" % (team_name, ge.status, ge.data["message"]))            