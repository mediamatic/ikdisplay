<h1>Sites</h1>

<table border="1">
    <tr>
        <th>Site name</th>
        <th>URI</th>
        <th>&nbsp;</th>
    </tr>
    
    {.repeated section @}
    <tr>
        <td>{title}</td>
        <td>{uri}</td>
        <td>
            <a href="javascript:;" onclick="BackChannel.actions.editItem({_id}, 'Edit site', 'Site')">edit</a>
            <a href="javascript:;" onclick="BackChannel.actions.removeItem({_id})">remove</a>
        </td>
    </tr>
    {.end}
</table>

<p>
    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.addSite();">Create new site</button>
</p>
