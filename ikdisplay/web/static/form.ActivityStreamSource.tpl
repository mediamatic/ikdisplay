<form dojoType="dijit.form.Form">
    <div>
        Site:
        <div dojoType="dojo.data.ItemFileReadStore" jsId="sites" url="/api/selectSites"></div>
        <select name="site" dojoType="dijit.form.FilteringSelect" store="sites" {.section site}value="{_id}"{.end} searchAttr="title" ></select>
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>
