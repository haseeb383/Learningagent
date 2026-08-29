import yaml

def _create_url(subject, year):
  URL_TEMPLATE = (
    "https://pastpapers.papacambridge.com/viewer/caie/"
    "{subject_slug}-{subject_code}-{year}-{session_name}-"
    "{subject_code}-{session_code}{yy}-{doc_type}-{paper}{variant}-pdf"
  )

  with open("datapipline/pastpapers/subject.yaml", "r") as file:
    subject_data = yaml.safe_load(file)[subject]

  papers = []
  for paper in subject_data['papers']:
    for variant in paper['variants']:
      for session in subject_data['sessions']:
        session_code, session_name = session
        record = {
          "qp_url": URL_TEMPLATE.format(
            subject_slug=subject_data['subject_slug'],
            subject_code=subject_data['subject_code'],
            year=year,
            session_name=session_name,
            session_code=session_code,
            yy=str(year)[-2:],
            doc_type="qp",
            paper=paper['number'],
            variant=variant,
          ),
          "ms_url": URL_TEMPLATE.format(
            subject_slug=subject_data['subject_slug'],
            subject_code=subject_data['subject_code'],
            year=year,
            session_name=session_name,
            session_code=session_code,
            yy=str(year)[-2:],
            doc_type="ms",
            paper=paper['number'],
            variant=variant,
          )
        }
        papers.append(record)
  return papers

papers = _create_url('mathematics_9709', 2026)
print(len(papers))
print(papers[71])
print(papers[71]['qp_url'])