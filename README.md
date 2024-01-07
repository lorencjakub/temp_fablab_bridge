# FABLAB BRIDGE

POC Flask bridge for online courses

*	Live demo: https://fablab-bridge-production.up.railway.app
*	Bridge swagger: https://fablab-bridge-production.up.railway.app/apidocs/

ClassMarker webhooks info:
*	https://www.classmarker.com/online-testing/docs/webhooks/#example-code
*	https://www.classmarker.com/online-testing/docs/webhooks/#link-results

<br>
<br>

## ENV VARIABLES:

*	FABMAN_API_KEY https://fabman.io/api/v1/documentation
*	MAX_COURSE_ATTEMPTS (global allowed counts of attempts of every course)
*	CLASSMARKER_WEBHOOK_SECRET https://www.classmarker.com/online-testing/docs/webhooks/#how-to-verify-webhook-payloads
*	FERNET_KEY crypto https://cryptography.io/en/latest/fernet/

<br>
<br>

## WORKFLOW 1 - GET ABSOLVED COURSES ON USER'S PROFILE PAGE
Get active (not expired) trainings of specific user for UI section "Absolved trainings".
![Absolved trainings workflow schema](/diagrams/absolved_trainings.jpg "Absolved trainings workflow schema")
<br>
<br>

### GET USER DATA, INCLUDING TRAININGS DATA:

*	Endpoint:  
	/members/<user_id>?embed=trainings&embed=privileges https://fabman.io/api/v1/documentation#/members/getMembersId

*	Data from response used in bridge function:  
```python
{
    "id": 12345,
    "lockVersion": 1,
    "metadata": {
        "failed_courses": [
            {
                "id": 123,
                "title": "Test2",
                "attempts": 1
            }
        ]
    },
    "_embedded": {
        "trainings": [
            {
                "id": 135,
                "lockVersion": 1,
                "trainingCourse": 456,
                "untilDate": null
            }
        ],
        "privileges": {
            "privileges": "member"
        }
    }
}
```

*Where*:
*	*"id": member ID in Fabman*
*	*"metadata" (default NULL) -> "failed_courses":*
	*	*counter for failed attempts of online course*
	*	*member is not able to absolve online course if failed attempts reached MAX_COURSE_ATTEMPTS value*
	*	*admin is able to update/reset attempts in Fabman portal*
*	*"_embedded" -> "trainings": list of absolved courses*

**Don't include course if**:  
*	**untilDate < today**
		
Return list of absolved training:  
*	"_embedded" -> "trainings"

<br>
<br>

TRY IT!  
https://fablab-bridge-production.up.railway.app/apidocs/#/absolved-trainings/get_absolved_trainings__member_id

<br>
<br>

## WORKFLOW 2 - GET AVAILABLE COURSES ON USER'S PROFILE PAGE
Get available (not absolved trainings or expired trainings) for specific user for UI section "Available trainings".
Some of trainings could be only for admins, some of them could be presence-only without online version.
User is not able to absolve online course if he is already out of attempts for it.
![Available trainings filter schema](/diagrams/available_trainings.jpg "Available trainings filter schema")
![Available trainings render schema](/diagrams/available_trainings_render.jpg "Available trainings render schema")
<br>
<br>

### GET USER DATA, INCLUDING TRAININGS DATA:
*	Endpoint:  
	https://fabman.io/api/v1/members/<user_id>?embed=trainings&embed=privileges (https://fabman.io/api/v1/documentation#/members/getMembersId)

*	Data from response used in bridge function:
``` python
{
    "id": 12345,
    "lockVersion": 1,
    "metadata": {
        "failed_courses": [
            {
                "id": 123,
                "title": "Test2",
                "attempts": 1
            }
        ]
    },
    "_embedded": {
        "trainings": [
            {
                "id": 135,
                "lockVersion": 1,
                "trainingCourse": 456,
                "untilDate": null
            }
        ],
        "privileges": {"privileges": "member"}
    }
}
```
	
*Where:*  
*	*"id": member ID in Fabman*
*	*"metadata" (default NULL) -> "failed_courses":*
	*	*counter for failed attempts of online course*
	*	*member is not able to absolve online course if failed attempts reached MAX_COURSE_ATTEMPTS value*
	*	*admin is able to update/reset attempts in Fabman portal*
*	*"_embedded" -> "trainings": list of absolved courses*

<br>
<br>

### GET LIST OF ALL COURSES:
*	Endpoint:  
	https://fabman.io/api/v1/training-courses/ (https://fabman.io/api/v1/documentation#/training-courses/getTrainingcourses)
	
*	Data from response used in bridge function:
``` python
{
    "id": 1234,
    "account": 1,
    "title": "Test Course",
    "notes": "<div>Test note</div>",
    "state": "active",
    "lockVersion": 1,
    "createdAt": "2023-09-30T12:20:54.771Z",
    "updatedAt": "2023-10-30T18:37:13.438Z",
    "updatedBy": 123456,
    "defaultDuration": 1,
    "defaultDurationUnit": "day",
    "metadata": {
        "cm_url": "https://www.classmarker.com/online-test/start/?quiz=XXXXXXXXXXXXXXXX",
        "admin_only": false,
        "not_online": false
    },
    "resources": [
        1234
    ]
}
```
		
**Don't include course if**:  
*	course already in member's trainings
*	"metadata" of member -> "failed_courses" -> "attempts" >= MAX_COURSE_ATTEMPTS
*	untilDate >= today
*	"_embedded" of member -> "privileges" is not "admin" and "metadata" of course -> "admin_only" is True
*	"metadata" of course -> "not_online" is True

<br>
<br>

#### Create URL links for courses:  
*	URL of ClassMarker quiz: "metadata" of course -> "cm_url" (for example "https://www.classmarker.com/online-test/start/?quiz=XXXXXXXXXXXXXXXX")
*	get member ID and course ID, create string in format "{member_id}-{course_id}" (for example "12345-100")
*	encrypt this string and add it as a query param "cm_user_id" in the URL (for example "https://www.classmarker.com/online-test/start/?quiz=XXXXXXXXXXXXXXXX&cm_user_id=encrypted<membed_id-training_id>")

TRY IT!  
https://fablab-bridge-production.up.railway.app/apidocs/#/cm-urls/post_create_cm_link

#### RETURN:
*	full URL link of ClassMarker quiz for current user and training:  
		"https://www.classmarker.com/online-test/start/?quiz=XXXXXXXXXXXXXXXX&cm_user_id=encrypted<membed_id-training_id>"
*	UI will render row for every of available courses with button with this URL as a href attribute

<br>
<br>

TRY IT!  
https://fablab-bridge-production.up.railway.app/apidocs/#/available-trainings/get_available_trainings__member_id_

<br>
<br>

## WORKFLOW 3 - ONLINE CLASSMARKER COURSE
Integration of process for online courses. Find available course in your user profile -> open quiz via href button -> pass that quiz -> ClassMarker webhook call to FabLab bridge -> handle online course attempt.
![Online training workflow schema](/diagrams/online_training.jpg "Online training workflow schema")
<br>
<br>
 
### CLASSMARKER WEBHOOK:
*	open ClassMarker quiz via course's href button
*	ClassMarker webhook calls bridge endpoint with results of quiz

<br>
<br>

### BRIDGE CALL:
*	https://www.classmarker.com/online-testing/docs/webhooks/#link-results
*	bridge endpoint: /add_classmarker_training/
*	request method: POST
*	request verification with "X-Classmarker-Hmac-Sha256" header: https://www.classmarker.com/online-testing/docs/webhooks/#how-to-verify-webhook-payloads
*	request payload - data used in bridge function:
``` python
{
    "test": {
        "test_name": string
    },
    "result": {
        "email": string,
        "passed": boolean,
        "cm_user_id": string ("encrypted<membed_id-training_id>")
    }
}
```

<br>
<br>

### USER NOTIFICATIONS (email, Discord, ...):
*	any exception during bridge operations (process failed, contact your FabLab CORE team)
*	process didn't failed, but user didn't pass ClassMarker quiz (info about remaining attempts or contact your FabLab CORE team because of attempts reset)
*	process succeed, training has been added

<br>
<br>

#### CASE 1 - USER DIDN'T PASS CLASSMARKER QUIZ:
*	get "metadata" a "lockVersion" from /members/{member_id}/
*	list "failed_courses" not in user's "metadata" -> create this list and insert current failed course:
	*	get course's data from /training-courses/{training_id}/
	*	format of course in list of failed_courses:
   		``` python
		{
		    "id": int (course ID from FabMan),
		    "title": str (course title from FabMan),
		    "attempts": int (default = 1)
		}
  		```
	*	list "failed_courses" in user's "metadata" contains current failed course -> check of "attempts":
		*	attempts >= MAX_COURSE_ATTEMPTS -> fail, Ran out of attempts
		*	attempts < MAX_COURSE_ATTEMPTS -> attempts +1
	*	update of user's metadata via PUT request:
		*	endpoint: /members/{member_id}
		*	body:
    		``` python
		{
		    "lockVersion": obtained from /members/{member_id}/,
		    "metadata": new metadata JSON
		}
		```
	*	return response 200, "Failed attempt saved in Fabman"

<br>
<br>

#### CASE 2 - USER PASSED CLASSMARKER QUIZ:
*	get user's data from /members/{member_id}?embed=trainings
*	current course in "embedded" -> "trainings”:
	*	untilDate > today -> response 400, "Member has already absolved this training and it is still active"
	*	untilDate <= today -> remember ID of course for next steps
*	update of member's trainings:
	*	endpoint: /members/{member_id}/trainings
	*	request method: POST
	*	request body:
 		``` python
		{
		    "date": today in format YYYY-MM-DD,
		    "fromDate": today in format YYYY-MM-DD,
		    "trainingCourse": training_id,
		    "notes": "Training absolved by Classmarker course"
		}
   		```
*	if current course is in "failed_courses" of member's "metadata":
	*	remove failed course from metadata:
		*	request endpoint: /members/{member_id}
		*	request method: PUT
		*	request body: metadata JSON without that course
	*	if ID of expired course from previous "embedded" -> "trainings” check is remembered:
		*	remove expired version of course from member:
			*	request endpoint: /members/{member_id}/trainings/{expired_training_id}
			*	request method: DELETE
	
	*	return response 200, "Training passed, updated in Fabman"

<br>
<br>

TRY IT!  
https://fablab-bridge-production.up.railway.app/apidocs/#/add-training/post_add_classmarker_training_ (hmac signature is required)

OR

CREATE YOUR UNIQUE URL (https://fablab-bridge-production.up.railway.app/apidocs/#/cm-urls/post_create_cm_link) AND TRY FULL PROCESS :)
