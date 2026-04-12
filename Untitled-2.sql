SELECT 
    c.id AS calendar_id,
    c.date AS fecha,
    c.day AS dia_semana,
    c.turn AS turno,
    c.overtime AS horas_extra,
    g.name AS nombre_grupo,
    u.nombre AS usuario_nombre,
    u.apellido AS usuario_apellido,
    u.rol AS usuario_rol,
    tga.taskp_id AS tarea_asignada_id
FROM 
    public.works4cdp_calendar c
LEFT JOIN 
    public.works4cdp_taskgroupassignment tga ON c.id = tga.calendar_id
LEFT JOIN 
    public.works4cdp_userp g ON c.group_id = g.id
LEFT JOIN 
    public.works4cdp_user u ON u.group_id = g.id OR u.id = c.id_user
ORDER BY 
    c.date ASC, 
    g.name ASC;