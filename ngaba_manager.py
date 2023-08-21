
from ctn_bpf.models import Owner

owners = Owner.objects.filter()
mail_lists = list()
for o in owners:
	mail_lists.append(o.m_user.mail)

with open('list_mail.txt', 'w') as f:
    for line in mail_lists:
        f.write(line)
        f.write('\n')
