classDiagram
direction BT
class auth_group {
   varchar(150) name
   integer id
}
class auth_group_permissions {
   integer group_id
   integer permission_id
   bigint id
}
class auth_permission {
   varchar(255) name
   integer content_type_id
   varchar(100) codename
   integer id
}
class auth_user {
   varchar(128) password
   timestamp with time zone last_login
   boolean is_superuser
   varchar(150) username
   varchar(150) first_name
   varchar(150) last_name
   varchar(254) email
   boolean is_staff
   boolean is_active
   timestamp with time zone date_joined
   integer id
}
class auth_user_groups {
   integer user_id
   integer group_id
   bigint id
}
class auth_user_user_permissions {
   integer user_id
   integer permission_id
   bigint id
}
class django_admin_log {
   timestamp with time zone action_time
   text object_id
   varchar(200) object_repr
   smallint action_flag
   text change_message
   integer content_type_id
   integer user_id
   integer id
}
class django_content_type {
   varchar(100) app_label
   varchar(100) model
   integer id
}
class django_migrations {
   varchar(255) app
   varchar(255) name
   timestamp with time zone applied
   bigint id
}
class django_session {
   text session_data
   timestamp with time zone expire_date
   varchar(40) session_key
}
class vequipment {
   bigint equipment_id
   varchar(100) equipment_name
   varchar(50) equipment_tag
   text equipment_description
   varchar(100) system_name
   varchar(100) area_name
   varchar(100) plant_name
}
class works4cdp_area {
   varchar(100) name
   varchar(10) tag
   text description
   bigint plant_id
   bigint id
}
class works4cdp_assay {
   date date
   time time
   integer instance
   integer n2cu
   integer n1fe
   integer n5ech5
   integer n4mo
   integer n3zn
   integer n6sc
   double precision pFe
   double precision pCu
   double precision pZn
   double precision pMo
   double precision pIns
   double precision pSol
   double precision tara
   double precision tweight
   double precision dweight
   double precision pweight
   integer chemical_id
   double precision a1fe
   double precision a4mo
   double precision a2cu
   double precision a3zn
   double precision a5a5
   varchar(50) meta_user
   bigint sample_id
   double precision a6sol
   double precision a7a7
   integer n7ech7
   bigint user_id
   bigint id
}
class works4cdp_assayspsi {
   date date
   time time
   integer instance
   double precision tara
   double precision tweight
   double precision dweight
   double precision psolid
   double precision pW48
   double precision pW65
   double precision pW100
   double precision pW150
   double precision pW200
   double precision pW325
   double precision pW400
   double precision aAvg
   double precision aSD
   double precision aDensity
   double precision aSol
   double precision aP48
   double precision aP65
   double precision aP100
   double precision aP150
   double precision aP200
   double precision aP325
   double precision aP400
   double precision P80
   double precision P50
   double precision pP48
   double precision pP65
   double precision pP100
   double precision pP150
   double precision pP200
   double precision pP325
   double precision pP400
   double precision an_50_um
   double precision a50_100_um
   double precision a100_150_um
   double precision a150_200_um
   double precision a200_250_um
   double precision a250_300_um
   double precision a300_350_um
   double precision a350_400_um
   double precision a400_450_um
   double precision a450_500_um
   double precision a500_550_um
   double precision a550_600_um
   double precision a600_650_um
   double precision a650_700_um
   double precision a700_750_um
   double precision a750_800_um
   double precision a800_850_um
   double precision a850_900_um
   double precision a900_950_um
   double precision a950_1000_um
   double precision a1000_n_um
   varchar(50) meta_user
   varchar(10) turn
   bigint sample_id
   bigint user_id
   bigint id
}
class works4cdp_calendar {
   integer year
   integer week
   varchar(20) day
   date date
   varchar(10) turn
   integer overtime
   bigint group_id
   bigint id_user
   bigint id
}
class works4cdp_correctivetask {
   text description
   date creation_date
   integer priority
   date completion_date
   text root_cause
   text comments
   bigint equipment_id
   bigint estado_id
   bigint created_by_user_id
   date date
   varchar(20) day
   integer week
   integer year
   bigint id
}
class works4cdp_equipment {
   varchar(50) tag
   varchar(100) name
   text description
   bigint system_id
   bigint area_id
   bigint id
}
class works4cdp_estado {
   varchar(50) estado_nombre
   bigint id
}
class works4cdp_plant {
   varchar(10) tag
   varchar(100) name
   text description
   bigint id
}
class works4cdp_sample {
   varchar(50) tag
   varchar(50) name
   bigint equipment_id
   varchar(4) sn
   bigint id
}
class works4cdp_system {
   varchar(50) tag
   varchar(100) name
   text description
   bigint id
}
class works4cdp_task {
   varchar(100) name
   integer duration
   integer workers
   varchar(50) frequency
   date start_date
   text description
   text procedure
   bigint equipment_id
   varchar(10) turn
   bigint id
}
class works4cdp_taskgroupassignment {
   bigint calendar_id
   bigint taskp_id
   bigint id
}
class works4cdp_taskp {
   integer year
   integer week
   varchar(20) day
   date date
   boolean rescheduled
   text reschedule_reason
   date reschedule_date
   integer reschedule_user_id
   bigint estado_id
   bigint task_id
   integer priority
   text comments
   timestamp with time zone completion_date
   boolean is_permanent_reschedule
   bigint usuario_id
   bigint id
}
class works4cdp_user {
   varchar(50) nombre
   varchar(50) apellido
   varchar(254) email
   varchar(50) rol
   integer auth_user_id
   bigint group_id
   bigint id
}
class works4cdp_userp {
   varchar(20) name
   bigint id
}

auth_group_permissions  -->  auth_group : group_id:id
auth_group_permissions  -->  auth_permission : permission_id:id
auth_permission  -->  django_content_type : content_type_id:id
auth_user_groups  -->  auth_group : group_id:id
auth_user_groups  -->  auth_user : user_id:id
auth_user_user_permissions  -->  auth_permission : permission_id:id
auth_user_user_permissions  -->  auth_user : user_id:id
django_admin_log  -->  auth_user : user_id:id
django_admin_log  -->  django_content_type : content_type_id:id
works4cdp_area  -->  works4cdp_plant : plant_id:id
works4cdp_assay  -->  works4cdp_sample : sample_id:id
works4cdp_assay  -->  works4cdp_user : user_id:id
works4cdp_assayspsi  -->  works4cdp_sample : sample_id:id
works4cdp_assayspsi  -->  works4cdp_user : user_id:id
works4cdp_calendar  -->  works4cdp_user : id_user:id
works4cdp_calendar  -->  works4cdp_userp : group_id:id
works4cdp_correctivetask  -->  works4cdp_equipment : equipment_id:id
works4cdp_correctivetask  -->  works4cdp_estado : estado_id:id
works4cdp_correctivetask  -->  works4cdp_user : created_by_user_id:id
works4cdp_equipment  -->  works4cdp_area : area_id:id
works4cdp_equipment  -->  works4cdp_system : system_id:id
works4cdp_sample  -->  works4cdp_equipment : equipment_id:id
works4cdp_task  -->  works4cdp_equipment : equipment_id:id
works4cdp_taskgroupassignment  -->  works4cdp_calendar : calendar_id:id
works4cdp_taskgroupassignment  -->  works4cdp_taskp : taskp_id:id
works4cdp_taskp  -->  works4cdp_estado : estado_id:id
works4cdp_taskp  -->  works4cdp_task : task_id:id
works4cdp_taskp  -->  works4cdp_userp : usuario_id:id
works4cdp_user  -->  auth_user : auth_user_id:id
works4cdp_user  -->  works4cdp_userp : group_id:id
