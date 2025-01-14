import { FunctionComponent } from "react"
import Link from "next/link"

import { AppstreamListItem } from "../../types/Appstream"

import ApplicationCard from "./ApplicationCard"
import Button from "../Button"
import { useTranslation } from "next-i18next"

interface Props {
  href: string
  title: string
  applications: AppstreamListItem[]
  showMore?: boolean
}

const ApplicationSection: FunctionComponent<Props> = ({
  href,
  title,
  applications,
  showMore = true,
}) => {
  const { t } = useTranslation()
  return (
    <div>
      <header className="mt-10 mb-3 flex max-w-full flex-row content-center justify-between">
        <h3 className="my-0">{title}</h3>

        {showMore && (
          <Link href={href} passHref>
            <a>
              <Button>{t("more")}</Button>
            </a>
          </Link>
        )}
      </header>
      <div className="grid grid-cols-2 justify-around gap-4 lg:grid-cols-3 2xl:grid-cols-6">
        {applications.map((app) => (
          <ApplicationCard key={app.id} application={app} />
        ))}
      </div>
    </div>
  )
}

export default ApplicationSection
