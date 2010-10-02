<ul>
    {.repeated section @}
    <li>Dit is een feed: <a href="#feed/{_id}">{title}</a>.</li>
    {.end}
</ul>

<p>
    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.addFeed();">Create new feed</button>
</p>
