<form dojoType="dijit.form.Form">
    <div>
        Agent:
        <div dojoType="dojo.data.ItemFileReadStore" jsId="things" url="/api/selectThings"></div>
        <select name="agent" dojoType="dijit.form.FilteringSelect" store="things" {.section agent}value="{_id}"{.end} searchAttr="title" ></select>
    </div>

    <div>
        Via:
        <input name="via" dojoType="dijit.form.TextBox" {.section via}value="{@}"{.end} />
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>
