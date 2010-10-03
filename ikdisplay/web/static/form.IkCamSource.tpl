<form dojoType="dijit.form.Form">
    <div>
        Pictures for event:
        <div dojoType="dojo.data.ItemFileReadStore" jsId="things" url="/api/selectThings"></div>
        <select name="event" required="false" dojoType="dijit.form.FilteringSelect" store="things" {.section event}value="{_id}"{.end} searchAttr="title" ></select>
    </div>

    <div>
        Pictures by user:
        <div dojoType="dojo.data.ItemFileReadStore" jsId="things" url="/api/selectThings"></div>
        <select name="creator" required="false" dojoType="dijit.form.FilteringSelect" store="things" {.section creator}value="{_id}"{.end} searchAttr="title" ></select>
    </div>

    <div>
        Via:
        <input name="via" dojoType="dijit.form.TextBox" {.section via}value="{@}"{.end} />
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>
