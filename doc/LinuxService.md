# Install as System Service 

Systemd service script to start the sorter server on startup

1) Take the example file `doc/sorter.service`
2) Copy it to `/lib/systemd/system/sorter.service`
2) Adapt the contain paths

Then reload the config and enable the service.
<pre>
sudo systemctl daemon-reload
sudo systemctl enable sorter.service
</pre>
To start, stop and check the status use
<pre>
sudo systemctl start sorter.service
sudo systemctl stop sorter.service
sudo systemctl status sorter.service
</pre>
The service should then start automatically on startup.
