/*
 * auto.js
 *
 * 作者: 苦叶子
 * charisma modified
 *
*/

/*
 * for string format
*/
String.prototype.lym_format = function() {
    if (arguments.length == 0) {
        return this;
    }
    for (var StringFormat_s = this, StringFormat_i = 0; StringFormat_i < arguments.length; StringFormat_i++) {
        StringFormat_s = StringFormat_s.replace(new RegExp("\\{" + StringFormat_i + "\\}", "g"), arguments[StringFormat_i]);
    }
    return StringFormat_s;
};

/*
 * to json
*/
$.fn.serializeObject = function() {
    var json = {};
    var arrObj = this.serializeArray();
    $.each(arrObj, function() {
      if (json[this.name]) {
           if (!json[this.name].push) {
            json[this.name] = [ json[this.name] ];
           }
           json[this.name].push(this.value || '');
      } else {
           json[this.name] = this.value || '';
      }
    });

    return json;
};

/*
 * 显示消息
*/
function show_msg(title, msg){
    $.messager.show({
        title: title,
        msg: msg,
        timeout: 3000,
        showType: 'slide'
    });
}

function do_refresh(data){
    location.href = data.url;
}

function do_nop(data){
    // 空函数
}

function do_msg(data){
    show_msg('Message', data.msg);
}

function do_init(data){
    if(data.data == ""){
        //editor.setValue("*** Settings ***\n\n\n*** Variables ***\n\n\n*** Test Cases ***\n\n\n*** Keywords ***\n\n");
        if(data.ext==".resource"){
            editor.setValue("*** Settings ***\n\n\n*** Variables ***\n\n\n");
        }
        else if(data.ext ==".robot"){
            editor.setValue("*** Settings ***\n\n\n*** Variables ***\n\n\n*** Test Cases ***\n\n\n*** Keywords ***\n\n");
        }
        else if(data.ext ==".yaml"){
            editor.setValue("Settings ***\n\n\nService\n\n\nExcutor\n\n\nseanarios\n\n");
        }
        else if(data.ext ==".py"){
            editor.setValue("# -*- coding: utf-8 -*-\n\n__author__ = \"chairsma\"\n\n");
        }
    }
    else{
        editor.setValue(data.data);
    }
}

function do_ajax(type, url, data, func){
    $.ajax({
        type : type,
        url : url,
        data: data,
        success : func
    });
}

function do_login(fm_id){
    var data = $('#{0}'.lym_format(fm_id)).serializeObject();
    do_ajax('post', '/api/v1/auth/', data, do_refresh);
}

function do_logout(username){
    do_ajax('get', '/api/v1/auth/', '', do_refresh)
}

function do_run(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var category = node.attributes["category"];
        var key = node.attributes["key"];
        var data ={"method": "run", "category": category, "key":key};
        if(category =="project"){
            data["project"] = node.attributes["name"];
        }
        else if(category == "suite"){
            var project = $('#project_tree').tree('getParent', node.target);
            data["project"] = project.attributes["name"];
            data["suite"] = node.attributes["name"];
        }
        else if(category == "case"){
            var suite = $('#project_tree').tree('getParent', node.target);
            var project = $('#project_tree').tree('getParent', suite.target);
            data["project"] = project.attributes["name"];
            data["suite"] = suite.attributes["name"];
            data["case"] = node.attributes["name"] + node.attributes['splitext'];
        }
        do_ajax('post',
            '/api/v1/task/',
            data,
            do_msg);
    }
}

function do_runpass(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var category = node.attributes["category"];
        var key = node.attributes["key"];
        var data ={"method": "runpass", "category": category, "key":key};
        do_ajax('post',
            '/api/v1/task/',
            data,
            do_msg);
    }
}

function do_runfail(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var category = node.attributes["category"];
        var key = node.attributes["key"];
        var data ={"method": "runfail", "category": category, "key":key};
        do_ajax('post',
            '/api/v1/task/',
            data,
            do_msg);
    }
}

function do_runtags(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    if(node){
        data["name"] = node.attributes['name'];
        data["key"] = node.attributes['key'];
        data["method"] = "runtags";
        do_ajax('post', '/api/v1/task/', data, do_msg);

        close_win(win_id);
    }
}

function do_runfile(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    if(node){
        data["name"] = node.attributes['name'];
        data["key"] = node.attributes['key'];
        data["method"] = "runfile";
        do_ajax('post', '/api/v1/task/', data, do_msg);

        close_win(win_id);
    }
}

function do_task_list(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var project = node.attributes["name"];
        addTab(project, "/task_list/{0}".lym_format(project), 'icon-task')
    }
}

function do_task_list_t(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var key = node.attributes["key"];
        addTab("Task List", "/task_list/{0}".lym_format(key.replace(/\//g,'--')), 'icon-task');
    }
}

function do_in_array(str, array){
    for(a in array){
        if(array[a] == str){
            return true;
        }
    }

    return false;
}

//charis:增加tab页面的，TODO 可以考虑根据splitext 更换不同icon
function onDblClick(node) {
    var category = node.attributes.category;
    var steps = new Array("library", "variable", "step", "user_keyword");
    if(category == "case"){
        var suite = $('#project_tree').tree('getParent', node.target);
        var project = $('#project_tree').tree('getParent', suite.target);
        addTab(node.attributes['name'], '/editor/{0}'.lym_format(
            node.attributes['key'].replace(/\//g,'--')
            ), "icon-editor");
        // charis added above
        //addTab(node.attributes['name'], '/editor/{0}/{1}/{2}{3}'.lym_format(
        //    project.attributes['name'],
        //    suite.attributes['name'],
        //    node.attributes['name'],
        //    node.attributes['splitext']
        //    ), "icon-editor");
    }
    else if(do_in_array(category, steps)){
        var testcase = $('#project_tree').tree('getParent', node.target);
        var suite = $('#project_tree').tree('getParent', testcase.target);
        var project = $('#project_tree').tree('getParent', suite.target);
        addTab(node.attributes['name'], '/editor/{0}'.lym_format(
            testcase.attributes['key'].replace(/\//g,'--')
            ), "icon-editor");
        //charis added above
        //addTab(testcase.attributes['name'], '/editor/{0}/{1}/{2}{3}'.lym_format(
        //    project.attributes['name'],
        //    suite.attributes['name'],
        //    testcase.attributes['name'],
        //    testcase.attributes['splitext']
        //    ), "icon-editor");
    }
    else if(category == "keyword"){
        var step = $('#project_tree').tree('getParent', node.target);
        var testcase = $('#project_tree').tree('getParent', step.target);
        var suite = $('#project_tree').tree('getParent', testcase.target);
        var project = $('#project_tree').tree('getParent', suite.target);
        addTab(node.attributes['name'], '/editor/{0}'.lym_format(
            testcase.attributes['key'].replace(/\//g,'--')
            ), "icon-editor");
        //charis added
        //addTab(testcase.attributes['name'], '/editor/{0}/{1}/{2}{3}'.lym_format(
        //    project.attributes['name'],
        //    suite.attributes['name'],
        //    testcase.attributes['name'],
        //    testcase.attributes['splitext']
        //    ), "icon-editor");
    }
}

function onContextMenu(e, node){
    e.preventDefault();
    // select the node
    $('#project_tree').tree('select', node.target);
    // display context menu

    $('#{0}_menu'.lym_format(node.attributes['category'])).menu('show', {
        left: e.pageX,
        top: e.pageY
    });
}

function addTab(title, url, icon){
    var editor_tabs = $("#editor_tabs");
    if (editor_tabs.tabs('exists', title)){
        //如果tab已经存在,则选中并刷新该tab: If tab exists, Select it and refresh.
        editor_tabs.tabs('select', title);
        refreshTab({title: title, url: url});
    }
    else {
        var content='<iframe scrolling="yes" frameborder="0"  src="{0}" style="width:100%;height:100%"></iframe>'.lym_format(url);
        editor_tabs.tabs('add',{
            title: title,
            closable: true,
            content: content,
            iconCls: icon||'icon-default'
        });
    }
}

function refreshTab(cfg){
    var tab = cfg.title?$('#editor_tabs').tabs('getTab',cfg.title):$('#editor_tabs').tabs('getSelected');
    if(tab && tab.find('iframe').length > 0){
        var frame = tab.find('iframe')[0];
        var url = cfg.url?cfg.url:fram.src;
        frame.contentWindow.location.href = url;
    }
}

function collapse(){
    var node = $('#project_tree').tree('getSelected');
    $('#project_tree').tree('collapse',node.target);
}

function expand(){
    var node = $('#project_tree').tree('getSelected');
    $('#project_tree').tree('expand',node.target);
}
function onClickToggle(node){
    var node = $('#project_tree').tree('getSelected');
    $('#project_tree').tree('toggle',node.target);
}


function onBeforeExpand(node){
    if(node){
        var param = $("#project_tree").tree("options").queryParams;
        param.category = node.attributes.category;
        param.key = node.attributes.key;
        param.name = node.attributes.name;
        if(node.attributes.category == "suite"){
            var parent = $("#project_tree").tree('getParent', node.target);
            param.project = parent.attributes.name;

        }
        else if(node.attributes.category == "case")
        {
            var suite = $("#project_tree").tree('getParent', node.target);
            param.suite = suite.attributes.name;
            var project = $("#project_tree").tree('getParent', suite.target);
            param.project = project.attributes.name;
            param.splitext = node.attributes.splitext;
        }
    }
}


function manage_project(win_id, ff_id, method){
    if(method == "create"){
        clear_form(ff_id);

    }
    if(method == "adduser"){
        clear_form(ff_id);

    }
    if(method == "deluser"){
        clear_form(ff_id);

    }
    else if(method == "edit"){
        var node = $('#project_tree').tree('getSelected');
        if(node){
            $("#{0} input#new_name".lym_format(ff_id)).textbox('setValue', node.attributes['name']);
        }
    }
    open_win(win_id);
}

function refresh_workspace(data){
    var param = $("#project_tree").tree("options").queryParams
    param.category = "root";
    param.key = "root";

    $('#project_tree').tree("reload");

    show_msg('Information', data.msg);
}

function refresh_project_node(data){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var param = $("#project_tree").tree("options").queryParams;
        param.category = "project";
        param.key = node.attributes.key;
        param.name = node.attributes.name;
        $('#project_tree').tree('reload', node.target);
    }
    show_msg('Information', data.msg);
}

function refresh_suite_node(data){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        parent = $('#project_tree').tree('getParent', node.target);

        var param = $("#project_tree").tree("options").queryParams;

        param.category = "project";
        param.key = node.attributes.key;
        param.name = parent.attributes.name;

        $('#project_tree').tree("reload", parent.target);
    }
    show_msg('Information', data.msg);
}

function refresh_suite_addtab_ORG(data){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        parent = $('#project_tree').tree('getParent', node.target);

        var param = $("#project_tree").tree("options").queryParams;

        param.category = "project";
        param.key = node.attributes.key;
        param.name = parent.attributes.name;

        $('#project_tree').tree("reload", parent.target);
    }
    //show_msg('Information', data.msg);
    //result = {"status": "success", "msg": "创建成功"+":"+os.path.basename(user_path)+":"+user_path}
    if(data.status == "fail"){
        show_msg('Information', data.msg);
    } else {
        var arr = data.msg.split(":");
        addTab(arr[1], '/editor/{0}'.lym_format(
            arr[2].replace(/\//g,'--')
            ), "icon-editor");
    }
}

function refresh_suite_addtab(data){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        parent = $('#project_tree').tree('getParent', node.target);

        var param = $("#project_tree").tree("options").queryParams;

        param.category = "suite";
        param.key = node.attributes.key;
        param.name = parent.attributes.name;

        $('#project_tree').tree("reload", node.target);
    }
    //show_msg('Information', data.msg);
    //result = {"status": "success", "msg": "创建成功"+":"+os.path.basename(user_path)+":"+user_path}
    if(data.status == "fail"){
        show_msg('Information', data.msg);
    } else {
        var arr = data.msg.split(":");
        addTab(arr[1], '/editor/{0}'.lym_format(
            arr[2].replace(/\//g,'--')
            ), "icon-editor");
    }
}

function refresh_case_node(data){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var param = $("#project_tree").tree("options").queryParams;
        param.category = "suite";
        param.key = node.attributes.key;
        var suite = $('#project_tree').tree('getParent', node.target);
        param.suite = suite.attributes.name
        var project = $("#project_tree").tree('getParent', suite.target);
        param.project = project.attributes.name;

        $('#project_tree').tree("reload", suite.target);
    }
    show_msg('Information', data.msg);
}

function create_project(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "create";

    do_ajax('post', '/api/v1/project/', data, refresh_workspace);

    close_win(win_id);
}

function create_projectgit(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "gitclone";

    do_ajax('post', '/api/v1/project/', data, refresh_workspace);

    close_win(win_id);
}

function rename_project(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    data["name"] = node.attributes['name'];
    data["key"] = node.attributes['key'];
    data["method"] = "edit";
    do_ajax('post', '/api/v1/project/', data, refresh_workspace);

    close_win(win_id);
}

function adduser_project(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    data["name"] = node.attributes['name'];
    data["key"] = node.attributes['key'];
    data["method"] = "adduser";
    do_ajax('post', '/api/v1/project/', data, do_msg);

    close_win(win_id);
}

function deluser_project(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    data["name"] = node.attributes['name'];
    data["key"] = node.attributes['key'];
    data["method"] = "deluser";
    do_ajax('post', '/api/v1/project/', data, do_msg);

    close_win(win_id);
}

function delete_project(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        $.messager.confirm('Alert', '<br>Are you sure Delete Project: {0}?'.lym_format(node.attributes['name']), function(r){
            if (r){
                var data = {
                        "name": node.attributes['name'],
                        "key": node.attributes['key'],
                        "method": "delete"
                    };

                do_ajax('post', "/api/v1/project/", data, refresh_workspace);
            }
        });
    }
}

function manage_suite(win_id, ff_id, method){
    if(method == "create"){
        clear_form(ff_id);

    }
    else if(method == "edit"){
        var node = $('#project_tree').tree('getSelected');
        if(node){
            $("#{0} input#new_name".lym_format(ff_id)).textbox('setValue', node.attributes['name']);
        }
    }
    open_win(win_id);
}

function refresh_suite_cases(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var suite = $('#project_tree').tree('getParent', node.target);
        var project = $('#project_tree').tree('getParent', suite.target);
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "refresh"
            };

        do_ajax('post', "/api/v1/suite/", data, refresh_case_node);
    }
}

function create_suite(win_id, ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = $("#{0}".lym_format(ff_id)).serializeObject();
        data["method"] = "create";
        data["key"] = node.attributes['key'];
        data["project_name"] = node.attributes['name'];

        do_ajax('post', '/api/v1/suite/', data, refresh_project_node);

        close_win(win_id);
    }
}

function create_suitegit(win_id, ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = $("#{0}".lym_format(ff_id)).serializeObject();
        data["method"] = "gitclone";
        data["key"] = node.attributes['key'];
        data["project_name"] = node.attributes['name'];

        do_ajax('post', '/api/v1/suite/', data, refresh_project_node);

        close_win(win_id);
    }
}

function rename_suite(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var project = $('#project_tree').tree('getParent', node.target);
        data["name"] = node.attributes['name'];
        data["key"] = node.attributes['key'];
        //charis added                        
        data["project_name"] = project.attributes['name'];
        data["method"] = "edit";
        do_ajax('post', '/api/v1/suite/', data, refresh_suite_node);

        close_win(win_id);
    }
}

function delete_suite(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        $.messager.confirm('Alert', '<br>Are you sure Delete Dir: {0}?'.lym_format(node.attributes['name']), function(r){
            if (r){
                var project = $('#project_tree').tree('getParent', node.target);
                var data = {
                        "name": node.attributes['name'],
                        "key": node.attributes['key'],     //实际上name 和 project name 属性在suite 的delete中都没有用到
                        "project_name": project.attributes['name'],
                        "method": "delete"
                    };

                do_ajax('post', "/api/v1/suite/", data, refresh_suite_node);
            }
        });
    }
}

function manage_file(win_id, ff_id, method){
    if(method == "create"){
        clear_form(ff_id);

    }
    else if(method == "edit"){
        var node = $('#project_tree').tree('getSelected');
        if(node){
            $("#{0} select#new_category".lym_format(ff_id)).combobox("setValue", node.attributes['splitext']);
            $("#{0} input#new_name".lym_format(ff_id)).textbox('setValue', node.attributes['name']);
        }
    }
    open_win(win_id);
}

function manage_run(win_id, ff_id, method){
    if(method == "runtags"){
        clear_form(ff_id);
    }
    else if(method == "runfile"){
        clear_form(ff_id);
    }
    open_win(win_id);
}

function create_file(win_id, ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var project = $('#project_tree').tree('getParent', node.target);
        var data = $("#{0}".lym_format(ff_id)).serializeObject();
        data["method"] = "create";
        data["suite_name"] = node.attributes['name'];
        data["project_name"] =  project.attributes['name'];
        data["key"] =  node.attributes['key'];

        do_ajax('post', '/api/v1/case/', data, refresh_suite_addtab);

        close_win(win_id);
    }
}

function rename_file(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var suite = $('#project_tree').tree('getParent', node.target);
        var project = $('#project_tree').tree('getParent', suite.target);
        data["name"] = node.attributes['name'];
        data["category"] = node.attributes['splitext'];
        data["key"] = node.attributes['key'];
        data["suite_name"] = suite.attributes['name'];
        data["project_name"] = project.attributes['name'];
        data["method"] = "edit";

        do_ajax('post', '/api/v1/case/', data, refresh_case_node);

        close_win(win_id);
    }
}


function delete_file(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        $.messager.confirm('Alert',
            '<br>确定删除文件: {0}{1}?'.lym_format(node.attributes['name'], node.attributes['splitext']),
            function(r){
                if (r){
                    var suite = $('#project_tree').tree('getParent', node.target);
                    var project = $('#project_tree').tree('getParent', suite.target);
                    var data = {
                            "name": node.attributes['name'],
                            "suite_name": suite.attributes['name'],
                            "project_name": project.attributes['name'],
                            "category": node.attributes['splitext'],
                            "key": node.attributes['key'],
                            "method": "delete"
                        };

                    do_ajax('post', "/api/v1/case/", data, refresh_case_node);
                }
        });
    }
}

function copy_casefile(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "copy"
            };

        do_ajax('post', "/api/v1/case/", data, refresh_case_node);
    }
}

function save_caserecord_d(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": "save_d_i_r",
                "key": node.attributes['key'],
                "method": "save_result"
            };
        do_ajax('post', "/api/v1/case/", data, do_msg);
    }
}

function save_caserecord(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "key": node.attributes['key'],
                "method": "save_result"
            };
        do_ajax('post', "/api/v1/case/", data, do_msg);
    }
}

function case_handpass(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "handpass"
            };
        do_ajax('post', "/api/v1/case/", data, refresh_case_node);
    }
}

function case_handfail(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "handfail"
            };
        do_ajax('post', "/api/v1/case/", data, refresh_case_node);
    }
}

function case_handunknown(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "handunknown"
            };
        do_ajax('post', "/api/v1/case/", data, refresh_case_node);
    }
}

function case_recordbug(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "recordbug"
            };
        do_ajax('post', "/api/v1/case/", data, refresh_case_node);
    }
}

function git_commit(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "gitcommit"
            };

        do_ajax('post', "/api/v1/suite/", data, refresh_case_node);
    }
}

function git_push(){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var data = {
                "name": node.attributes['name'],
                "category": node.attributes['splitext'],
                "key": node.attributes['key'],
                "method": "gitpush"
            };

        do_ajax('post', "/api/v1/suite/", data, refresh_case_node);
    }
}

function do_upload(win_id, ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var project = $('#project_tree').tree('getParent', node.target);
        //charis added
        $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(node.attributes['key']));
        //$("#{0} input#path".lym_format(ff_id)).val("/{0}/{1}/".lym_format(project.attributes['name'], node.attributes['name']));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {
                //var node = $('#project_tree').tree('getSelected');
                var d = JSON.parse(result);
                //show_msg('Information', d.msg);
                refresh_suite_node(d);
                close_win(win_id);
            }
        });
    }
}

function do_uploadcase(win_id, ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(node.attributes['key']));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {
                var d = JSON.parse(result);
                //show_msg('Information', d.msg);
                refresh_suite_node(d);
                close_win(win_id);
            }
        });
    }
}

function do_exportresult_d(ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var key = node.attributes['key'];
        var name = "export_d_i_r";
        $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
        $("#{0} input#name".lym_format(ff_id)).val("{0}".lym_format(name));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
        });
    }
}

function do_exportresult_c(ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node){
        var key = node.attributes['key'];
        var name = node.attributes['name'];
        $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
        $("#{0} input#name".lym_format(ff_id)).val("{0}".lym_format(name));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
        });
    }
}

function do_exportresult(ff_id){
    var row = $('#case_list').datagrid('getSelected');
    var key = row.info_key;
    var name = row.info_name;

    $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
    $("#{0} input#name".lym_format(ff_id)).val("{0}".lym_format(name));
    $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
    });
}

function do_download(ff_id){
    var node = $('#project_tree').tree('getSelected');
    if(node && node.attributes['category'] == 'case'){
        var key = node.attributes['key']
        $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
        });
    }
}

function do_downcaseinfox(ff_id){
    var node = $('#project_tree').tree('getSelected');
    var key = node.attributes['key']
    var method = "downcaseinfox"
    $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
    $("#{0} input#method".lym_format(ff_id)).val("{0}".lym_format(method));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
        });
}

function do_downcaseinfoz(ff_id){
    var node = $('#project_tree').tree('getSelected');
    var key = node.attributes['key']
    var method = "downcaseinfoz"
    $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
    $("#{0} input#method".lym_format(ff_id)).val("{0}".lym_format(method));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
        });
}

function do_downruninfo(ff_id){
    var node = $('#project_tree').tree('getSelected');
    var key = node.attributes['key']
    $("#{0} input#key".lym_format(ff_id)).val("{0}".lym_format(key));
        $("#{0}".lym_format(ff_id)).form('submit', {
            success: function (result) {

            }
        });
}

function show_img(value, row, index){
    return '<img width="24px" height="24px" border="0" src="{0}"/>'.lym_format(value) ;
}

function do_open_editor(){
    var node = $('#project_tree').tree('getSelected');
    if(node && node.attributes['category'] == 'case'){
        var suite = $('#project_tree').tree('getParent', node.target);
        var project = $('#project_tree').tree('getParent', suite.target);
        addTab(node.attributes['name'], '/editor/{0}'.lym_format(
            node.attributes['key'].replace(/\//g,'--')
            ), "icon-editor");
        //charis added above
    }
}

function do_casereport(){
    var node = $('#project_tree').tree('getSelected');
    addTab(node.attributes['name']+"- Case Report", '/casereport/{0}'.lym_format(
            node.attributes['key'].replace(/\//g,'--')
            ), "icon-list");
}

function do_caselist(){
    var node = $('#project_tree').tree('getSelected');
    addTab(node.attributes['name']+"- Case List", '/caselist/{0}'.lym_format(
            node.attributes['key'].replace(/\//g,'--')
            ), "icon-list");
}

function do_excutereport(){
    var node = $('#project_tree').tree('getSelected');
    addTab(node.attributes['name']+"- Execution Report", '/excutereport/{0}'.lym_format(
            node.attributes['key'].replace(/\//g,'--')
            ), "icon-list");
}


function refresh_user_list(data){
    $('#user_list').datagrid("reload");
    show_msg('Information', data.msg);
}

function refresh_setting_list(data){
    $('#setting_list').datagrid("reload");
    show_msg('Information', data.msg);
}

function manage_setting(win_id, ff_id, method){
    if(method == "create"){
        clear_form(ff_id);
    }
    else if(method == "edit"){

    }
    open_win(win_id);
}

function create_setting(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "create";

    do_ajax('post', '/api/v1/settings/', data, refresh_setting_list);

    close_win(win_id);
}

function edit_setting(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "edit";

    do_ajax('post', '/api/v1/settings/', data, refresh_setting_list);

    close_win(win_id);
}

function manage_user(win_id, ff_id, method){
    if(method == "create"){
        clear_form(ff_id);

    }
    else if(method == "edit"){

    }
    open_win(win_id);
}

function create_user(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "create";

    do_ajax('post', '/api/v1/user/', data, refresh_user_list);

    close_win(win_id);
}

function edit_user(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "edit";

    do_ajax('post', '/api/v1/user/', data, refresh_user_list);

    close_win(win_id);
}

function close_win(id){
    $('#{0}'.lym_format(id)).window('close');
}

function open_win(id){
    $('#{0}'.lym_format(id)).window('open');
}

function clear_form(id){
    $('#{0}'.lym_format(id)).form('clear');
}

function load_smtp(data){
    $("#edit_smtp_ff").form("load", data);
    $("#edit_smtp_ff input#ssl").prop("checked", data["ssl"]);
}

function init_smtp_ff(){
    var data = {"method": "smtp"};
    do_ajax('get', '/api/v1/settings/', data, load_smtp);
}

function load_email(data){
    $("#notify_ff").form("load", data);
}

function init_email_ff(name){
    var data = {"method": "email", "project": name};
    do_ajax('get', '/api/v1/settings/', data, load_email);
}

function do_smtp(win_id, ff_id){
    var data = $("#{0}".lym_format(ff_id)).serializeObject();
    data["method"] = "smtp";

    do_ajax('post', '/api/v1/settings/', data, do_nop);

    close_win(win_id);
}