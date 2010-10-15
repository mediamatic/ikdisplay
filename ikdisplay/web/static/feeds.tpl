<h1>Feeds</h1>

<table class="list feeds">
    <tr>
        <th>Feed name</th>
        <th>URI</th>
        <th class="actions">&nbsp;</th>
    </tr>
    
    {.repeated section @}
    <tr>
        <td><a href="#feed/{_id}">{title}</a></td>
        <td>{_uri}</td>
        <td>
            <a href="javascript:;" onclick="BackChannel.actions.editItem({_id}, 'Edit feed', 'Feed')">edit</a>
            <a href="javascript:;" onclick="BackChannel.actions.removeItem({_id})">remove</a>
        </td>
    </tr>
    {.end}
</table>

<p>
    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.addFeed();">Create new feed</button>
</p>
