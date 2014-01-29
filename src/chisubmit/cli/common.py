from chisubmit.core.repos import GradingGitRepo
from chisubmit.core import ChisubmitException, handle_unexpected_exception
from chisubmit.common import CHISUBMIT_FAIL, CHISUBMIT_SUCCESS

def get_teams(course, project, grader = None, only = None):
    if only is not None:
        team = course.get_team(only)
        if team is None:
            print "Team %s does not exist"
            return None
        if not team.has_project(project):
            print "Team %s has not been assigned project %s" % project.id
            return None
        
        teams = [team]
    else:
        teams = [t for t in course.teams.values() if t.has_project(project.id)]  
        
        if grader is not None:
            teams = [t for t in teams if t.get_project(project.id).grader == grader]        

    return teams  


def create_grading_repos(course, project, teams, grader = None):
    repos = []
   
    for team in teams:
        try:
            repo = GradingGitRepo.get_grading_repo(course, team, project)
            
            if repo is None:
                print ("Creating grading repo for %s... " % team.id),
                repo = GradingGitRepo.create_grading_repo(course, team, project)
                
                repos.append(repo)
                
                print "done"
            else:
                print "Grading repo for %s already exists" % team.id
        except ChisubmitException, ce:
            raise ce # Propagate upwards, it will be handled by chisubmit_cmd
        except Exception, e:
            handle_unexpected_exception()
            
    return repos
            

def gradingrepo_push_grading_branch(course, team, project, github=False, staging=False):
    try:    
        repo = GradingGitRepo.get_grading_repo(course, team, project)
        
        if repo is None:
            print "%s does not have a grading repository" % team.id
            return CHISUBMIT_FAIL
            
        if github:
            repo.push_grading_branch_to_github()
            
        if staging:
            repo.push_grading_branch_to_staging()
    except ChisubmitException, ce:
        raise ce # Propagate upwards, it will be handled by chisubmit_cmd
    except Exception, e:
        handle_unexpected_exception()

    return CHISUBMIT_SUCCESS

def gradingrepo_pull_grading_branch(course, team, project, github=False, staging=False):
    try:
        repo = GradingGitRepo.get_grading_repo(course, team, project)
        
        if repo is None:
            print "%s does not have a grading repository" % team.id
            return CHISUBMIT_FAIL
        
        if github:
            repo.pull_grading_branch_from_github()
        
        if staging:
            repo.pull_grading_branch_from_staging()
            
    except ChisubmitException, ce:
        raise ce # Propagate upwards, it will be handled by chisubmit_cmd
    except Exception, e:
        handle_unexpected_exception()
        
    return CHISUBMIT_SUCCESS                